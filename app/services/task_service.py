"""
Task Service

业务逻辑层：处理任务状态管理相关的业务逻辑。
包括任务状态查询、更新、完成和失败处理。
"""

import base64
import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import TaskStatus, TaskType
from app.repositories import ImageRepository
from app.schemas import (
    ImageData,
    TaskStatusData,
    TaskStatusResponse,
    ErrorResponse,
)
from app.services.task_query_service import TaskQueryService
from app.infra.apimart_client import ApimartClient
from app.infra.apimart_errors import ApimartError

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

    def __init__(self, session: AsyncSession, apimart_client: ApimartClient | None = None):
        """
        初始化任务服务

        Args:
            session: 数据库会话
            apimart_client: Apimart 客户端（可选）
        """
        self.session = session
        self.image_repo = ImageRepository(session)
        self.query_service = TaskQueryService(session)
        self._apimart_client = apimart_client or ApimartClient()
        self._settings = get_settings()
        self._http_client: httpx.AsyncClient | None = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端用于下载图片"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=self._settings.http_timeout,
            )
        return self._http_client

    async def _download_image_as_base64(self, image_url: str) -> str | None:
        """下载图片并转换为 Base64"""
        try:
            client = await self._get_http_client()
            response = await client.get(image_url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "image/png")
            image_data = base64.b64encode(response.content).decode("utf-8")
            return f"data:{content_type};base64,{image_data}"
        except Exception as e:
            logger.warning(f"Failed to download image: {e}")
            return None

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
        获取任务状态
        
        如果任务未完成，会同步从 Apimart 获取最新状态并更新数据库。

        Args:
            task_id: 任务 ID (格式: task_xxxxxxx)

        Returns:
            TaskStatusResponse: 任务状态响应

        Raises:
            TaskNotFoundError: 任务不存在

        Requirements: 3.4
        """
        result = await self.query_service.find_by_task_id(task_id)
        if result is None:
            raise TaskNotFoundError(task_id)

        # 如果任务还在进行中，同步从 Apimart 获取最新状态
        if result.status in (TaskStatus.SUBMITTED, TaskStatus.PROCESSING):
            result = await self._sync_task_status_from_apimart(task_id, result)

        # 构建图片信息（如果任务已完成）
        image_data = None
        if result.status == TaskStatus.COMPLETED:
            image = await self.image_repo.get_by_task(result.task_type, result.id)
            if image:
                image_data = ImageData(
                    image_base64=image.image_base64,
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

    async def _sync_task_status_from_apimart(self, task_id: str, current_result):
        """
        从 Apimart 同步任务状态并更新数据库
        
        Args:
            task_id: Apimart 任务 ID
            current_result: 当前数据库中的任务结果
            
        Returns:
            更新后的任务结果
        """
        try:
            apimart_status = await self._apimart_client.get_task_status(task_id)
            
            if apimart_status.is_completed:
                # 任务完成 - 下载图片并更新数据库
                logger.info(f"Task {task_id} completed, syncing from Apimart")
                
                image_base64: str | None = None
                image_url: str | None = None
                
                if apimart_status.image_urls:
                    image_url = apimart_status.image_urls[0]
                    image_base64 = await self._download_image_as_base64(image_url)
                
                # 更新任务状态
                await self.query_service.update_status(task_id, TaskStatus.COMPLETED, 100)
                
                # 创建图片记录
                await self.image_repo.create(
                    task_type=current_result.task_type,
                    task_id=current_result.id,
                    angle=current_result.angle,
                    image_base64=image_base64,
                    image_url=image_url,
                )
                
                await self.session.commit()
                
                # 重新获取更新后的结果
                return await self.query_service.find_by_task_id(task_id)
                
            elif apimart_status.is_failed:
                # 任务失败 - 更新数据库
                error_msg = apimart_status.error
                if isinstance(error_msg, dict):
                    error_msg = error_msg.get("message", str(error_msg))
                error_msg = str(error_msg) if error_msg else "Unknown error"
                
                logger.error(f"Task {task_id} failed: {error_msg}")
                await self.query_service.update_status(task_id, TaskStatus.FAILED, error_message=error_msg)
                await self.session.commit()
                
                return await self.query_service.find_by_task_id(task_id)
                
            else:
                # 任务进行中 - 更新进度
                if current_result.status == TaskStatus.SUBMITTED:
                    await self.query_service.update_status(task_id, TaskStatus.PROCESSING, apimart_status.progress)
                    await self.session.commit()
                    return await self.query_service.find_by_task_id(task_id)
                elif current_result.progress != apimart_status.progress:
                    await self.query_service.update_status(task_id, TaskStatus.PROCESSING, apimart_status.progress)
                    await self.session.commit()
                    return await self.query_service.find_by_task_id(task_id)
                    
        except ApimartError as e:
            logger.warning(f"Failed to sync task {task_id} from Apimart: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error syncing task {task_id}: {e}")
        
        # 如果同步失败，返回原始结果
        return current_result

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
        image_base64: str | None = None,
        image_url: str | None = None,
    ) -> None:
        """
        完成任务 - 使用 TaskQueryService 统一更新

        Args:
            task_id: 任务 ID (格式: task_xxxxxxx)
            image_base64: 图片 Base64 数据
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
            image_base64=image_base64,
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
