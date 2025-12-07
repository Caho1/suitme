"""
Image Repository

数据访问层：图片表的 CRUD 操作封装。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AIGenerationImage


class ImageRepository:
    """图片数据访问仓库"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        task_id: int,
        angle: str | None = None,
        image_base64: str | None = None,
        image_url: str | None = None,
    ) -> AIGenerationImage:
        """
        创建图片记录

        Args:
            task_id: 关联的任务 ID
            angle: 视角
            image_base64: 图片 Base64 数据
            image_url: 图片 OSS URL

        Returns:
            创建的图片对象
        """
        image = AIGenerationImage(
            task_id=task_id,
            angle=angle,
            image_base64=image_base64,
            image_url=image_url,
        )
        self.session.add(image)
        await self.session.flush()
        await self.session.refresh(image)
        return image

    async def get_by_task_id(self, task_id: int) -> AIGenerationImage | None:
        """
        根据任务 ID 获取图片

        Args:
            task_id: 任务 ID

        Returns:
            图片对象，不存在则返回 None
        """
        result = await self.session.execute(
            select(AIGenerationImage).where(AIGenerationImage.task_id == task_id)
        )
        return result.scalar_one_or_none()

    async def get_all_by_task_id(self, task_id: int) -> list[AIGenerationImage]:
        """
        根据任务 ID 获取所有图片

        Args:
            task_id: 任务 ID

        Returns:
            图片对象列表
        """
        result = await self.session.execute(
            select(AIGenerationImage).where(AIGenerationImage.task_id == task_id)
        )
        return list(result.scalars().all())
