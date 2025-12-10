"""
回调处理器

实现 Java 后端回调通知功能：
- 任务完成/失败时通知 Java 后端
- 身份验证 token 添加到请求头
- 指数退避重试逻辑
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class CallbackError(Exception):
    """回调错误"""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass
class CallbackPayload:
    """回调请求体"""
    task_id: int
    status: str
    type: str
    angle: str | None = None
    image_base64: str | None = None
    image_url: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典，排除 None 值（Requirements: 4.2）"""
        return {
            k: v for k, v in {
                "task_id": self.task_id,
                "status": self.status,
                "type": self.type,
                "angle": self.angle,
                "image_base64": self.image_base64,
                "image_url": self.image_url,
                "error_message": self.error_message,
            }.items() if v is not None
        }


class CallbackHandler:
    """Java 后端回调处理器"""

    def __init__(self, http_client: httpx.AsyncClient | None = None):
        """
        初始化回调处理器

        Args:
            http_client: 可选的 httpx 异步客户端，用于测试注入
        """
        self._settings = get_settings()
        self._http_client = http_client

    async def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._http_client:
            return self._http_client
        return httpx.AsyncClient(
            timeout=self._settings.http_timeout,
        )

    def _build_headers(self) -> dict[str, str]:
        """
        构建请求头，包含身份验证 token

        Returns:
            dict: 请求头字典

        Requirements: 7.3
        """
        headers = {
            "Content-Type": "application/json",
        }
        if self._settings.callback_token:
            headers["Authorization"] = f"Bearer {self._settings.callback_token}"
        return headers

    async def notify_java(
        self,
        task_id: int,
        status: str,
        task_type: str,
        angle: str | None = None,
        image_base64: str | None = None,
        image_url: str | None = None,
        error_message: str | None = None,
    ) -> bool:
        """
        通知 Java 后端任务完成或失败

        Args:
            task_id: 任务 ID
            status: 任务状态 (completed/failed)
            task_type: 任务类型 (default/edit/outfit)
            angle: 视角 (仅穿搭任务)
            image_base64: 图片 Base64 数据
            image_url: 图片 OSS URL
            error_message: 错误信息 (失败时)

        Returns:
            bool: 回调是否成功

        Raises:
            CallbackError: 回调失败且重试耗尽

        Requirements: 7.1, 7.2, 7.3
        """
        if not self._settings.callback_url:
            logger.warning("Callback URL not configured, skipping notification")
            return False

        payload = CallbackPayload(
            task_id=task_id,
            status=status,
            type=task_type,
            angle=angle,
            image_base64=image_base64,
            image_url=image_url,
            error_message=error_message,
        )

        return await self._send_with_retry(payload)

    async def _send_with_retry(self, payload: CallbackPayload) -> bool:
        """
        带重试的回调发送

        Args:
            payload: 回调请求体

        Returns:
            bool: 是否成功

        Raises:
            CallbackError: 重试耗尽后抛出

        Requirements: 7.2
        """
        max_retries = self._settings.callback_max_retries
        base_delay = self._settings.retry_base_delay
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                await self._send_callback(payload)
                logger.info(
                    f"Callback sent successfully for task {payload.task_id}"
                )
                return True
            except Exception as e:
                last_error = e
                if attempt == max_retries - 1:
                    logger.error(
                        f"Callback failed after {max_retries} attempts "
                        f"for task {payload.task_id}: {e}"
                    )
                    raise CallbackError(
                        f"Callback failed after {max_retries} retries: {e}",
                        status_code=getattr(e, "status_code", None),
                    )

                # 指数退避
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    f"Callback attempt {attempt + 1}/{max_retries} failed "
                    f"for task {payload.task_id}: {e}. Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)

        # 理论上不会到达这里
        if last_error:
            raise CallbackError(f"Callback failed: {last_error}")
        return False

    async def _send_callback(self, payload: CallbackPayload) -> None:
        """
        发送单次回调请求

        Args:
            payload: 回调请求体

        Raises:
            CallbackError: HTTP 请求失败
        """
        client = await self._get_client()
        try:
            response = await client.post(
                self._settings.callback_url,
                json=payload.to_dict(),
                headers=self._build_headers(),
            )

            if response.status_code >= 400:
                raise CallbackError(
                    f"Callback returned error: {response.status_code} - {response.text}",
                    status_code=response.status_code,
                )
        except httpx.TimeoutException as e:
            raise CallbackError(f"Callback timeout: {e}")
        except httpx.ConnectError as e:
            raise CallbackError(f"Callback connection error: {e}")
        finally:
            if not self._http_client:
                await client.aclose()
