"""
阿里云 OSS 客户端

封装与阿里云 OSS 的交互，包括：
- 下载远程图片
- 上传图片到 OSS
- 生成 OSS URL
"""

import asyncio
import logging
import uuid
from datetime import datetime
from io import BytesIO
from typing import Optional

import httpx
import alibabacloud_oss_v2 as oss

from app.config import get_settings

logger = logging.getLogger(__name__)


class OSSClient:
    """阿里云 OSS 客户端"""

    def __init__(self):
        """初始化 OSS 客户端"""
        self._settings = get_settings()
        self._client: Optional[oss.Client] = None
        self._http_client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> oss.Client:
        """获取 OSS Client 实例"""
        if self._client is None:
            cfg = oss.config.load_default()
            cfg.credentials_provider = oss.credentials.StaticCredentialsProvider(
                access_key_id=self._settings.oss_access_key_id,
                access_key_secret=self._settings.oss_access_key_secret,
            )
            cfg.endpoint = f"https://{self._settings.oss_endpoint}"
            cfg.region = self._settings.oss_endpoint.split(".")[0].replace("oss-", "")
            self._client = oss.Client(cfg)
        return self._client

    async def _get_http_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=self._settings.http_timeout,
            )
        return self._http_client

    def _generate_object_key(self, task_id: str, extension: str = "png") -> str:
        """
        生成 OSS 对象 Key
        
        格式: images/{year}/{month}/{day}/{task_id}_{uuid}.{ext}
        """
        now = datetime.now()
        unique_id = uuid.uuid4().hex[:8]
        return f"images/{now.year}/{now.month:02d}/{now.day:02d}/{task_id}_{unique_id}.{extension}"

    def _get_extension_from_content_type(self, content_type: str) -> str:
        """从 Content-Type 获取文件扩展名"""
        mapping = {
            "image/jpeg": "jpg",
            "image/jpg": "jpg",
            "image/png": "png",
            "image/gif": "gif",
            "image/webp": "webp",
            "image/bmp": "bmp",
        }
        return mapping.get(content_type.lower().split(";")[0].strip(), "png")

    async def download_and_upload(self, image_url: str, task_id: str) -> str | None:
        """
        下载远程图片并上传到 OSS
        
        Args:
            image_url: 远程图片 URL
            task_id: 任务 ID（用于生成文件名）
            
        Returns:
            OSS URL，失败返回 None
        """
        try:
            # 下载图片
            client = await self._get_http_client()
            response = await client.get(image_url)
            response.raise_for_status()
            
            content_type = response.headers.get("content-type", "image/png")
            extension = self._get_extension_from_content_type(content_type)
            image_data = response.content
            
            # 生成 OSS Key
            object_key = self._generate_object_key(task_id, extension)
            
            # 上传到 OSS（同步操作，在线程池中执行）
            oss_client = self._get_client()
            
            def _upload():
                request = oss.models.PutObjectRequest(
                    bucket=self._settings.oss_bucket,
                    key=object_key,
                    body=BytesIO(image_data),
                    content_type=content_type,
                )
                return oss_client.put_object(request)
            
            await asyncio.to_thread(_upload)
            
            # 生成 OSS URL
            oss_url = f"https://{self._settings.oss_bucket}.{self._settings.oss_endpoint}/{object_key}"
            logger.info(f"Uploaded image to OSS: {oss_url}")
            
            return oss_url
            
        except Exception as e:
            logger.error(f"Failed to download and upload image: {e}")
            return None

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
