"""
Apimart API 客户端

封装与 Apimart Images API 的交互，包括：
- 提交图像生成任务
- 查询任务状态
- 错误处理和重试
"""

import httpx
from typing import Any

from app.config import get_settings
from app.infra.apimart_errors import (
    ApimartErrorHandler,
    with_retry,
)


class ApimartTaskStatus:
    """Apimart 任务状态响应"""

    def __init__(self, data: dict[str, Any]):
        self.status: str = data.get("status", "")
        self.progress: int = data.get("progress", 0)
        self.error: str | dict | None = data.get("error")  # 可能是字符串或字典
        self.result: dict[str, Any] | None = data.get("result")

    @property
    def is_completed(self) -> bool:
        return self.status == "completed"

    @property
    def is_failed(self) -> bool:
        return self.status == "failed"

    @property
    def is_pending(self) -> bool:
        return self.status in ("submitted", "processing")

    @property
    def image_urls(self) -> list[str]:
        """获取生成的图片 URL 列表"""
        if not self.result:
            return []
        images = self.result.get("images", [])
        urls = []
        for img in images:
            url_list = img.get("url", [])
            if url_list:
                urls.extend(url_list)
        return urls


class ApimartClient:
    """Apimart API 客户端"""

    def __init__(self, http_client: httpx.AsyncClient | None = None):
        """
        初始化 Apimart 客户端

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
            base_url=self._settings.apimart_base_url,
            headers={
                "Authorization": f"Bearer {self._settings.apimart_api_key}",
                "Content-Type": "application/json",
            },
            timeout=self._settings.http_timeout,
        )

    async def submit_generation(
        self,
        prompt: str,
        image_urls: list[str],
        model: str = "gemini-3-pro-image-preview",
        size: str = "4:3",
        n: int = 1,
    ) -> str:
        """
        提交图像生成任务

        Args:
            prompt: 生成提示词
            image_urls: 输入图片 URL 或 Base64 Data URI 列表
            model: 模型名称
            size: 图片尺寸比例
            n: 生成数量

        Returns:
            str: Apimart 任务 ID (external_task_id)

        Raises:
            ApimartError: API 调用失败时抛出
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "n": n,
            "image_urls": [{"url": url} for url in image_urls],
        }

        async def _do_submit() -> str:
            client = await self._get_client()
            try:
                response = await client.post("/images/generations", json=payload)
                ApimartErrorHandler.handle_response_error(response)
                data = response.json()
                # Apimart 返回格式: {"code":200,"data":[{"status":"submitted","task_id":"..."}]}
                return data["data"][0]["task_id"]
            finally:
                if not self._http_client:
                    await client.aclose()

        return await with_retry(_do_submit)

    async def get_task_status(self, external_task_id: str) -> ApimartTaskStatus:
        """
        查询任务状态

        Args:
            external_task_id: Apimart 任务 ID

        Returns:
            ApimartTaskStatus: 任务状态对象

        Raises:
            ApimartError: API 调用失败时抛出
        """
        async def _do_get_status() -> ApimartTaskStatus:
            client = await self._get_client()
            try:
                response = await client.get(f"/tasks/{external_task_id}")
                ApimartErrorHandler.handle_response_error(response)
                data = response.json()
                # Apimart 返回格式: {"code": 200, "data": {"status": "...", "result": {...}}}
                return ApimartTaskStatus(data["data"])
            finally:
                if not self._http_client:
                    await client.aclose()

        return await with_retry(_do_get_status)
