"""
Task Service

业务逻辑层：处理任务状态管理相关的业务逻辑。
包括任务状态查询、更新、完成和失败处理。
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TaskStatus, TaskType
from app.repositories import ImageRepository
from app.schemas import (
    ImageData,
    TaskStatusData,
    TaskStatusResponse,
    ErrorResponse,
)
from app.services.task_query_service import TaskQueryService

logger = logging.getLogger(__name__)


class TaskNotFoundError(Exception):
    """任务不存在异常"""

    def __init__(self, task_id: str):
        self.task_id = task_id
        super().__init__(f"Task not found: {task_id}")


class InvalidStatusTransitionError(Exception):
    """无效的状态转换异常"""

    def __init__(self, current_status: TaskStatus, target_status: TaskStatus):
        self.current_status = current_status
        self.target_status = target_status
        super().__init__(
            f"Invalid status transition: {current_status.value} -> {target_status.value}"
        )


# 有效的状态转换映射
VALID_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.SUBMITTED: {TaskStatus.PROCESSING, TaskStatus.FAILED},
    TaskStatus.PROCESSING: {TaskStatus.COMPLETED, TaskStatus.FAILED},
    TaskStatus.COMPLETED: set(),  # 终态，不能转换
    TaskStatus.FAILED: set(),  # 终态，不能转换
}


class TaskService:
    """任务状态管理服务"""

    def __init__(self, session: AsyncSession):
        """
        初始化任务服务

        Args:
            session: 数据库会话
        """
        self.session = session
        self.image_repo = ImageRepository(session)
        self.query_service = TaskQueryService(session)

    def _validate_status_transition(
        self,
        current_status: TaskStatus,
        target_status: TaskStatus,
    ) -> None:
        """
        验证状态转换是否有效

        Args:
            current_status: 当前状态
            target_status: 目标状态

        Raises:
            InvalidStatusTransitionError: 状态转换无效
        """
        valid_targets = VALID_TRANSITIONS.get(current_status, set())
        if target_status not in valid_targets:
            raise InvalidStatusTransitionError(current_status, target_status)

    async def get_task_status(self, task_id: str) -> TaskStatusResponse:
        """
        获取任务状态（只读查询）
        
        直接返回数据库中的状态，不主动同步 Apimart。
        状态更新由后台 TaskPoller 负责。

        Args:
            task_id: 本地任务 ID (格式: task_xxxxxxx)

        Returns:
            TaskStatusResponse: 任务状态响应

        Raises:
            TaskNotFoundError: 任务不存在

        Requirements: 3.4
        """
        result = await self.query_service.find_by_task_id(task_id)
        if result is None:
            raise TaskNotFoundError(task_id)

        # 构建图片信息（如果任务已完成）
        image_data = None
        if result.status == TaskStatus.COMPLETED:
            image = await self.image_repo.get_by_task(result.task_type, result.id)
            if image:
                image_data = ImageData(
                    image_url=image.image_url,
                )

        return TaskStatusResponse(
            code=0,
            msg="success",
            data=TaskStatusData(
                task_id=result.task_id,
                status=result.status.value,
                progress=result.progress,
                type=result.task_type.value,
                angle=result.angle,
                image=image_data,
                error_message=result.error_message,
            ),
        )

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress: int | None = None,
    ) -> None:
        """
        更新任务状态 - 使用 TaskQueryService 统一更新

        Args:
            task_id: 任务 ID (格式: task_xxxxxxx)
            status: 新状态
            progress: 进度百分比

        Raises:
            TaskNotFoundError: 任务不存在
            InvalidStatusTransitionError: 状态转换无效

        Requirements: 4.2
        """
        result = await self.query_service.find_by_task_id(task_id)
        if result is None:
            raise TaskNotFoundError(task_id)

        # 验证状态转换
        self._validate_status_transition(result.status, status)

        # 使用 TaskQueryService 统一更新
        await self.query_service.update_status(task_id, status, progress)

    async def complete_task(
        self,
        task_id: str,
        image_url: str | None = None,
    ) -> None:
        """
        完成任务 - 使用 TaskQueryService 统一更新

        Args:
            task_id: 任务 ID (格式: task_xxxxxxx)
            image_url: 图片 OSS URL

        Raises:
            TaskNotFoundError: 任务不存在
            InvalidStatusTransitionError: 状态转换无效

        Requirements: 4.3
        """
        result = await self.query_service.find_by_task_id(task_id)
        if result is None:
            raise TaskNotFoundError(task_id)

        # 验证状态转换（只能从 PROCESSING 转换到 COMPLETED）
        self._validate_status_transition(result.status, TaskStatus.COMPLETED)

        # 使用 TaskQueryService 统一更新
        updated_result = await self.query_service.update_status(task_id, TaskStatus.COMPLETED, 100)

        # 创建图片记录（使用内部数据库 ID 和任务类型）
        await self.image_repo.create(
            task_type=result.task_type,
            task_id=result.id,
            angle=result.angle,
            image_url=image_url,
        )

    async def fail_task(
        self,
        task_id: str,
        error_message: str,
    ) -> None:
        """
        标记任务失败 - 使用 TaskQueryService 统一更新

        Args:
            task_id: 任务 ID (格式: task_xxxxxxx)
            error_message: 错误信息

        Raises:
            TaskNotFoundError: 任务不存在
            InvalidStatusTransitionError: 状态转换无效

        Requirements: 4.4
        """
        result = await self.query_service.find_by_task_id(task_id)
        if result is None:
            raise TaskNotFoundError(task_id)

        # 验证状态转换（可以从 SUBMITTED 或 PROCESSING 转换到 FAILED）
        self._validate_status_transition(result.status, TaskStatus.FAILED)

        # 使用 TaskQueryService 统一更新
        await self.query_service.update_status(task_id, TaskStatus.FAILED, error_message=error_message)
