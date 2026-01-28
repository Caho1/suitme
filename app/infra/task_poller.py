"""
任务轮询器

实现异步任务状态轮询，包括：
- 启动轮询
- 轮询循环
- 任务完成处理（获取图片 URL、上传 OSS）

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
"""

import asyncio
import logging

from typing import Callable, Awaitable

from app.config import get_settings
from app.models import TaskStatus
from app.infra.apimart_client import ApimartClient, ApimartTaskStatus
from app.infra.apimart_errors import ApimartError, ApimartErrorHandler
from app.infra.oss_client import OSSClient

logger = logging.getLogger(__name__)


class TaskPollerError(Exception):
    """任务轮询错误"""
    pass


class TaskPoller:
    """
    任务轮询器
    
    负责轮询 Apimart 任务状态，处理任务完成/失败，
    并在任务结束时触发回调。
    """

    @staticmethod
    def _extract_error_message(error: str | dict | None) -> str:
        """
        从 Apimart 错误响应中提取错误消息
        
        处理以下情况：
        - string: 直接返回
        - dict with "message" key: 返回 message 值
        - dict without "message" key: 返回 dict 的字符串表示
        - None: 返回默认错误消息
        
        Args:
            error: 错误值，可能是字符串、字典或 None
            
        Returns:
            str: 非空的错误消息字符串
            
        Requirements: 4.1
        """
        if isinstance(error, dict):
            return error.get("message", str(error))
        if error:
            return str(error)
        return "Unknown error from Apimart"

    def __init__(
        self,
        apimart_client: ApimartClient | None = None,
        oss_client: OSSClient | None = None,
        on_task_completed: Callable[[str, str | None], Awaitable[None]] | None = None,
        on_task_failed: Callable[[str, str], Awaitable[None]] | None = None,
        on_task_progress: Callable[[str, TaskStatus, int], Awaitable[None]] | None = None,
    ):
        """
        初始化任务轮询器

        Args:
            apimart_client: Apimart 客户端，用于查询任务状态
            oss_client: OSS 客户端，用于上传图片
            on_task_completed: 任务完成回调 (task_id, oss_url)
            on_task_failed: 任务失败回调 (task_id, error_message)
            on_task_progress: 任务进度更新回调 (task_id, status, progress)
        """
        self._settings = get_settings()
        self._apimart_client = apimart_client or ApimartClient()
        self._oss_client = oss_client or OSSClient()
        self._on_task_completed = on_task_completed
        self._on_task_failed = on_task_failed
        self._on_task_progress = on_task_progress
        self._active_polls: dict[str, asyncio.Task] = {}

    @property
    def poll_interval(self) -> float:
        """轮询间隔（秒）"""
        return self._settings.task_poll_interval

    async def close(self) -> None:
        """关闭资源"""
        # 关闭 OSS 客户端
        if self._oss_client:
            await self._oss_client.close()
        
        # 取消所有活跃的轮询任务
        for task_id, poll_task in list(self._active_polls.items()):
            if not poll_task.done():
                poll_task.cancel()
                try:
                    await poll_task
                except asyncio.CancelledError:
                    pass
        self._active_polls.clear()

    async def start_polling(
        self,
        apimart_task_id: str,
        local_task_id: str | None = None,
    ) -> None:
        """
        启动任务轮询

        Args:
            apimart_task_id: Apimart 任务 ID（用于查询 Apimart）
            local_task_id: 本地任务 ID（用于更新数据库，如果为 None 则使用 apimart_task_id）

        Requirements: 4.1
        """
        # 使用 local_task_id 作为回调的 task_id
        callback_task_id = local_task_id or apimart_task_id
        
        if apimart_task_id in self._active_polls:
            logger.warning(f"Task {apimart_task_id} is already being polled")
            return

        logger.info(f"Starting polling for task {apimart_task_id} (local: {callback_task_id})")
        
        # 创建轮询任务
        poll_task = asyncio.create_task(
            self._poll_loop(apimart_task_id, callback_task_id)
        )
        self._active_polls[apimart_task_id] = poll_task

    async def _poll_loop(
        self,
        apimart_task_id: str,
        callback_task_id: str,
    ) -> None:
        """
        轮询循环

        持续轮询直到 Apimart 返回完成或失败状态。

        Args:
            apimart_task_id: Apimart 任务 ID（用于查询）
            callback_task_id: 回调使用的任务 ID（本地 task_id）

        Requirements: 4.1, 4.2, 4.3, 4.4
        """
        try:
            while True:
                try:
                    # 查询 Apimart 任务状态
                    status = await self._apimart_client.get_task_status(apimart_task_id)
                    
                    if status.is_completed:
                        # 任务完成
                        logger.info(f"Task {apimart_task_id} completed")
                        await self._handle_completed(callback_task_id, status)
                        return
                    
                    elif status.is_failed:
                        # 任务失败 - 提取错误消息
                        error_msg = self._extract_error_message(status.error)
                        logger.error(f"Task {apimart_task_id} failed: {error_msg}")
                        await self._handle_failed(callback_task_id, error_msg)
                        return
                    
                    else:
                        # 任务进行中，更新进度
                        await self._handle_progress(callback_task_id, status)

                except ApimartError as e:
                    logger.error(f"Apimart error while polling task {apimart_task_id}: {e}")
                    # 不可重试的错误直接失败；可重试错误继续轮询
                    if not ApimartErrorHandler.is_retryable(e):
                        await self._handle_failed(callback_task_id, str(e))
                        return

                except Exception as e:
                    logger.exception(f"Unexpected error while polling task {apimart_task_id}: {e}")
                    # 继续轮询，不因为单次错误而放弃

                # 等待下一次轮询
                await asyncio.sleep(self.poll_interval)

        finally:
            # 清理活跃轮询记录
            self._active_polls.pop(apimart_task_id, None)

    async def _handle_progress(
        self,
        task_id: str,
        status: ApimartTaskStatus,
    ) -> None:
        """
        处理任务进度更新

        Args:
            task_id: 任务 ID (格式: task_xxxxxxx)
            status: Apimart 任务状态

        Requirements: 4.2
        """
        # 映射 Apimart 状态到内部状态
        internal_status = TaskStatus.PROCESSING
        
        if self._on_task_progress:
            await self._on_task_progress(task_id, internal_status, status.progress)

    async def _handle_completed(
        self,
        task_id: str,
        status: ApimartTaskStatus,
    ) -> None:
        """
        处理任务完成

        获取图片 URL 并上传到 OSS。

        Args:
            task_id: 任务 ID (格式: task_xxxxxxx)
            status: Apimart 任务状态

        Requirements: 4.3, 1.5, 8.2
        """
        oss_url: str | None = None

        # 获取图片 URL
        image_urls = status.image_urls
        if image_urls:
            source_url = image_urls[0]  # 取第一张图片
            
            # 下载图片并上传到 OSS
            try:
                oss_url = await self._oss_client.download_and_upload(source_url, task_id)
            except Exception as e:
                logger.warning(f"Failed to upload image to OSS for task {task_id}: {e}")

        if self._on_task_completed:
            await self._on_task_completed(task_id, oss_url)

    async def _handle_failed(
        self,
        task_id: str,
        error_message: str,
    ) -> None:
        """
        处理任务失败

        Args:
            task_id: 任务 ID (格式: task_xxxxxxx)
            error_message: 错误信息

        Requirements: 4.4
        """
        if self._on_task_failed:
            await self._on_task_failed(task_id, error_message)

    def is_polling(self, task_id: str) -> bool:
        """
        检查任务是否正在轮询

        Args:
            task_id: 任务 ID (格式: task_xxxxxxx)

        Returns:
            bool: 是否正在轮询
        """
        return task_id in self._active_polls and not self._active_polls[task_id].done()

    def get_active_poll_count(self) -> int:
        """
        获取活跃轮询任务数量

        Returns:
            int: 活跃轮询数量
        """
        return sum(1 for task in self._active_polls.values() if not task.done())
