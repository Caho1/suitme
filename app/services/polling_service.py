"""
Polling Service

业务逻辑层：集成 TaskPoller 与数据库操作。
负责启动轮询、处理任务完成/失败、更新数据库状态。

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 1.5, 8.2
"""

import logging
from typing import Callable, Awaitable

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TaskStatus, TaskType
from app.repositories import ImageRepository
from app.infra.task_poller import TaskPoller
from app.infra.apimart_client import ApimartClient
from app.services.task_query_service import TaskQueryService

logger = logging.getLogger(__name__)


class PollingService:
    """
    轮询服务
    
    集成 TaskPoller 与数据库操作，提供完整的任务轮询生命周期管理。
    """

    def __init__(
        self,
        session: AsyncSession,
        apimart_client: ApimartClient | None = None,
        on_callback: Callable[[int, str, str | None], Awaitable[None]] | None = None,
    ):
        """
        初始化轮询服务

        Args:
            session: 数据库会话
            apimart_client: Apimart 客户端
            on_callback: 任务完成/失败后的回调函数 (task_id, status, error_message)
        """
        self.session = session
        self.query_service = TaskQueryService(session)
        self.image_repo = ImageRepository(session)
        self._on_callback = on_callback
        
        # 创建 TaskPoller，注入回调函数
        self._poller = TaskPoller(
            apimart_client=apimart_client,
            on_task_completed=self._handle_task_completed,
            on_task_failed=self._handle_task_failed,
            on_task_progress=self._handle_task_progress,
        )

    async def close(self) -> None:
        """关闭资源"""
        await self._poller.close()

    async def start_polling(self, task_id: str) -> None:
        """
        启动任务轮询

        Args:
            task_id: Apimart 任务 ID

        Requirements: 4.1
        """
        await self._poller.start_polling(task_id)

    async def _handle_task_progress(
        self,
        task_id: str,
        status: TaskStatus,
        progress: int,
    ) -> None:
        """
        处理任务进度更新 - 使用 TaskQueryService 统一更新

        Args:
            task_id: Apimart 任务 ID
            status: 任务状态
            progress: 进度百分比

        Requirements: 4.2
        """
        try:
            result = await self.query_service.find_by_task_id(task_id)
            if result is None:
                logger.error(f"Task {task_id} not found for progress update")
                return

            # 只有当状态需要更新时才更新
            if result.status == TaskStatus.SUBMITTED:
                await self.query_service.update_status(task_id, TaskStatus.PROCESSING, progress)
                await self.session.commit()
                logger.info(f"Task {task_id} status updated to PROCESSING, progress: {progress}%")
            elif result.status == TaskStatus.PROCESSING and result.progress != progress:
                await self.query_service.update_status(task_id, TaskStatus.PROCESSING, progress)
                await self.session.commit()
                logger.debug(f"Task {task_id} progress updated to {progress}%")

        except Exception as e:
            logger.exception(f"Error updating task {task_id} progress: {e}")
            await self.session.rollback()

    async def _handle_task_completed(
        self,
        task_id: str,
        oss_url: str | None,
    ) -> None:
        """
        处理任务完成 - 使用 TaskQueryService 统一更新

        将 OSS URL 写入 generation_image 表。

        Args:
            task_id: Apimart 任务 ID
            oss_url: 图片 OSS URL

        Requirements: 4.3, 1.5, 8.2
        """
        try:
            result = await self.query_service.update_status(task_id, TaskStatus.COMPLETED, 100)
            if result is None:
                logger.error(f"Task {task_id} not found for completion")
                return

            # 创建图片记录（只存储 OSS URL）
            await self.image_repo.create(
                task_type=result.task_type,
                task_id=result.id,
                angle=result.angle,
                image_url=oss_url,
            )

            await self.session.commit()
            logger.info(f"Task {task_id} completed and image saved to OSS: {oss_url}")

            # 触发回调
            if self._on_callback:
                await self._on_callback(result.id, "completed", None)

        except Exception as e:
            logger.exception(f"Error completing task {task_id}: {e}")
            await self.session.rollback()

    async def _handle_task_failed(
        self,
        task_id: str,
        error_message: str,
    ) -> None:
        """
        处理任务失败 - 使用 TaskQueryService 统一更新

        Args:
            task_id: Apimart 任务 ID
            error_message: 错误信息

        Requirements: 4.4, 4.5
        """
        try:
            result = await self.query_service.update_status(
                task_id, TaskStatus.FAILED, error_message=error_message
            )
            if result is None:
                logger.error(f"Task {task_id} not found for failure handling")
                return

            await self.session.commit()
            logger.info(f"Task {task_id} marked as failed: {error_message}")

            # 触发回调
            if self._on_callback:
                await self._on_callback(result.id, "failed", error_message)

        except Exception as e:
            logger.exception(f"Error handling task {task_id} failure: {e}")
            await self.session.rollback()

    def is_polling(self, task_id: str) -> bool:
        """检查任务是否正在轮询"""
        return self._poller.is_polling(task_id)

    def get_active_poll_count(self) -> int:
        """获取活跃轮询任务数量"""
        return self._poller.get_active_poll_count()
