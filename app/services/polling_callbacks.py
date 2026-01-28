"""
Polling callbacks

提供给 TaskPoller 使用的回调函数：在独立数据库会话中更新任务状态与图片记录。

说明：
- 回调函数不依赖请求生命周期，避免使用路由注入的 session。
- 便于在应用启动时统一创建单例 TaskPoller，并在重启后恢复轮询。
"""

import logging

from app.database import get_db_session_context
from app.models import TaskStatus
from app.repositories import ImageRepository
from app.services.task_query_service import TaskQueryService

logger = logging.getLogger(__name__)


async def on_task_progress(task_id: str, status: TaskStatus, progress: int) -> None:
    """任务进度更新回调（独立会话）"""
    try:
        async with get_db_session_context() as session:
            query_service = TaskQueryService(session)
            await query_service.update_status(task_id, TaskStatus.PROCESSING, progress)
    except Exception as exc:
        logger.exception(f"Failed to update progress for task {task_id}: {exc}")


async def on_task_completed(task_id: str, oss_url: str | None) -> None:
    """任务完成回调（独立会话）"""
    try:
        async with get_db_session_context() as session:
            query_service = TaskQueryService(session)
            image_repo = ImageRepository(session)

            result = await query_service.update_status(task_id, TaskStatus.COMPLETED, 100)
            if result:
                await image_repo.create(
                    task_type=result.task_type,
                    task_id=result.id,
                    angle=result.angle,
                    image_url=oss_url,
                )
    except Exception as exc:
        logger.exception(f"Failed to handle task completion for {task_id}: {exc}")


async def on_task_failed(task_id: str, error_message: str) -> None:
    """任务失败回调（独立会话）"""
    try:
        async with get_db_session_context() as session:
            query_service = TaskQueryService(session)
            await query_service.update_status(task_id, TaskStatus.FAILED, error_message=error_message)
    except Exception as exc:
        logger.exception(f"Failed to handle task failure for {task_id}: {exc}")

