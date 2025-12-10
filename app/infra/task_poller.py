"""
任务轮询器

实现异步任务状态轮询，包括：
- 启动轮询
- 轮询循环
- 任务完成处理（下载图片、存储）
- 超时处理

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
"""

import asyncio
import base64
import logging
from datetime import datetime, timezone
from typing import Callable, Awaitable

import httpx

from app.config import get_settings
from app.models import TaskStatus
from app.infra.apimart_client import ApimartClient, ApimartTaskStatus
from app.infra.apimart_errors import ApimartError

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
        on_task_completed: Callable[[str, str | None, str | None], Awaitable[None]] | None = None,
        on_task_failed: Callable[[str, str], Awaitable[None]] | None = None,
        on_task_progress: Callable[[str, TaskStatus, int], Awaitable[None]] | None = None,
    ):
        """
        初始化任务轮询器

        Args:
            apimart_client: Apimart 客户端，用于查询任务状态
            on_task_completed: 任务完成回调 (task_id, image_base64, image_url)
            on_task_failed: 任务失败回调 (task_id, error_message)
            on_task_progress: 任务进度更新回调 (task_id, status, progress)
        """
        self._settings = get_settings()
        self._apimart_client = apimart_client or ApimartClient()
        self._on_task_completed = on_task_completed
        self._on_task_failed = on_task_failed
        self._on_task_progress = on_task_progress
        self._active_polls: dict[str, asyncio.Task] = {}
        self._http_client: httpx.AsyncClient | None = None

    @property
    def poll_interval(self) -> float:
        """轮询间隔（秒）"""
        return self._settings.task_poll_interval

    @property
    def task_timeout(self) -> float:
        """任务超时时间（秒）"""
        return self._settings.task_timeout

    async def _get_http_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端用于下载图片"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=self._settings.http_timeout,
            )
        return self._http_client

    async def close(self) -> None:
        """关闭资源"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        
        # 取消所有活跃的轮询任务
        for task_id, poll_task in self._active_polls.items():
            if not poll_task.done():
                poll_task.cancel()
                try:
                    await poll_task
                except asyncio.CancelledError:
                    pass
        self._active_polls.clear()

    async def start_polling(
        self,
        task_id: str,
    ) -> None:
        """
        启动任务轮询

        Args:
            task_id: Apimart 任务 ID

        Requirements: 4.1
        """
        if task_id in self._active_polls:
            logger.warning(f"Task {task_id} is already being polled")
            return

        logger.info(f"Starting polling for task {task_id}")
        
        # 创建轮询任务
        poll_task = asyncio.create_task(
            self._poll_loop(task_id)
        )
        self._active_polls[task_id] = poll_task

    async def _poll_loop(
        self,
        task_id: str,
    ) -> None:
        """
        轮询循环

        Args:
            task_id: Apimart 任务 ID

        Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            while True:
                # 检查超时
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                if elapsed > self.task_timeout:
                    logger.error(f"Task {task_id} timed out after {elapsed:.1f}s")
                    await self._handle_timeout(task_id)
                    return

                try:
                    # 查询 Apimart 任务状态
                    status = await self._apimart_client.get_task_status(task_id)
                    
                    if status.is_completed:
                        # 任务完成
                        logger.info(f"Task {task_id} completed")
                        await self._handle_completed(task_id, status)
                        return
                    
                    elif status.is_failed:
                        # 任务失败 - 提取错误消息
                        error_msg = self._extract_error_message(status.error)
                        logger.error(f"Task {task_id} failed: {error_msg}")
                        await self._handle_failed(task_id, error_msg)
                        return
                    
                    else:
                        # 任务进行中，更新进度
                        await self._handle_progress(task_id, status)

                except ApimartError as e:
                    logger.error(f"Apimart error while polling task {task_id}: {e}")
                    # 如果是不可重试的错误，标记任务失败
                    if not e.should_alert:
                        await self._handle_failed(task_id, str(e))
                        return
                    # 可重试错误继续轮询

                except Exception as e:
                    logger.exception(f"Unexpected error while polling task {task_id}: {e}")
                    # 继续轮询，不因为单次错误而放弃

                # 等待下一次轮询
                await asyncio.sleep(self.poll_interval)

        finally:
            # 清理活跃轮询记录
            self._active_polls.pop(task_id, None)

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

        下载图片并存储为 Base64 或 URL。

        Args:
            task_id: 任务 ID (格式: task_xxxxxxx)
            status: Apimart 任务状态

        Requirements: 4.3, 1.5, 8.2
        """
        image_base64: str | None = None
        image_url: str | None = None

        # 获取图片 URL
        image_urls = status.image_urls
        if image_urls:
            image_url = image_urls[0]  # 取第一张图片
            
            # 下载图片并转换为 Base64
            try:
                image_base64 = await self._download_image_as_base64(image_url)
            except Exception as e:
                logger.warning(f"Failed to download image for task {task_id}: {e}")
                # 即使下载失败，也保存 URL

        if self._on_task_completed:
            await self._on_task_completed(task_id, image_base64, image_url)

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

    async def _handle_timeout(
        self,
        task_id: str,
    ) -> None:
        """
        处理任务超时

        Args:
            task_id: 任务 ID (格式: task_xxxxxxx)

        Requirements: 4.5
        """
        await self._handle_failed(task_id, "timeout")

    async def _download_image_as_base64(self, image_url: str) -> str:
        """
        下载图片并转换为 Base64

        Args:
            image_url: 图片 URL

        Returns:
            str: Base64 编码的图片数据（Data URI 格式）

        Requirements: 1.5
        """
        client = await self._get_http_client()
        response = await client.get(image_url)
        response.raise_for_status()
        
        # 获取 Content-Type
        content_type = response.headers.get("content-type", "image/png")
        
        # 转换为 Base64
        image_data = base64.b64encode(response.content).decode("utf-8")
        
        # 返回 Data URI 格式
        return f"data:{content_type};base64,{image_data}"

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
