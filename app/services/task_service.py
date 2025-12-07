"""
Task Service

业务逻辑层：处理任务状态管理相关的业务逻辑。
包括任务状态查询、更新、完成和失败处理。
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TaskStatus
from app.repositories.task_repository import TaskRepository
from app.repositories.image_repository import ImageRepository
from app.schemas import (
    ImageData,
    TaskStatusData,
    TaskStatusResponse,
    ErrorResponse,
)


class TaskNotFoundError(Exception):
    """任务不存在异常"""

    def __init__(self, task_id: int):
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
        self.task_repo = TaskRepository(session)
        self.image_repo = ImageRepository(session)

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

    async def get_task_status(self, task_id: int) -> TaskStatusResponse:
        """
        获取任务状态

        Args:
            task_id: 任务 ID

        Returns:
            TaskStatusResponse: 任务状态响应

        Raises:
            TaskNotFoundError: 任务不存在

        Requirements: 5.1, 5.2, 5.3
        """
        task = await self.task_repo.get_by_id(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)

        # 构建图片信息（如果任务已完成）
        image_data = None
        if task.status == TaskStatus.COMPLETED:
            image = await self.image_repo.get_by_task_id(task_id)
            if image:
                image_data = ImageData(
                    image_base64=image.image_base64,
                    image_url=image.image_url,
                )

        return TaskStatusResponse(
            code=0,
            msg="success",
            data=TaskStatusData(
                task_id=task.id,
                status=task.status.value,
                progress=task.progress,
                type=task.type.value,
                angle=task.angle,
                image=image_data,
                error_message=task.error_message,
            ),
        )

    async def update_task_status(
        self,
        task_id: int,
        status: TaskStatus,
        progress: int | None = None,
    ) -> None:
        """
        更新任务状态

        Args:
            task_id: 任务 ID
            status: 新状态
            progress: 进度百分比

        Raises:
            TaskNotFoundError: 任务不存在
            InvalidStatusTransitionError: 状态转换无效

        Requirements: 4.2
        """
        task = await self.task_repo.get_by_id(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)

        # 验证状态转换
        self._validate_status_transition(task.status, status)

        # 更新状态
        await self.task_repo.update_status(
            task_id=task_id,
            status=status,
            progress=progress,
        )

    async def complete_task(
        self,
        task_id: int,
        image_base64: str | None = None,
        image_url: str | None = None,
    ) -> None:
        """
        完成任务

        Args:
            task_id: 任务 ID
            image_base64: 图片 Base64 数据
            image_url: 图片 OSS URL

        Raises:
            TaskNotFoundError: 任务不存在
            InvalidStatusTransitionError: 状态转换无效

        Requirements: 4.3
        """
        task = await self.task_repo.get_by_id(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)

        # 验证状态转换（只能从 PROCESSING 转换到 COMPLETED）
        self._validate_status_transition(task.status, TaskStatus.COMPLETED)

        # 更新任务状态
        await self.task_repo.update_status(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            progress=100,
        )

        # 创建图片记录
        await self.image_repo.create(
            task_id=task_id,
            angle=task.angle,
            image_base64=image_base64,
            image_url=image_url,
        )

    async def fail_task(
        self,
        task_id: int,
        error_message: str,
    ) -> None:
        """
        标记任务失败

        Args:
            task_id: 任务 ID
            error_message: 错误信息

        Raises:
            TaskNotFoundError: 任务不存在
            InvalidStatusTransitionError: 状态转换无效

        Requirements: 4.4
        """
        task = await self.task_repo.get_by_id(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)

        # 验证状态转换（可以从 SUBMITTED 或 PROCESSING 转换到 FAILED）
        self._validate_status_transition(task.status, TaskStatus.FAILED)

        # 更新任务状态
        await self.task_repo.update_status(
            task_id=task_id,
            status=TaskStatus.FAILED,
            error_message=error_message,
        )
