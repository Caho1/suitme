"""
Image Repository

数据访问层：图片表的 CRUD 操作封装。
支持多态查询，通过 task_type 区分不同任务类型的图片。
"""

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GenerationImage, TaskType

logger = logging.getLogger(__name__)


class ImageRepository:
    """图片数据访问仓库"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        task_type: TaskType,
        task_id: int,
        angle: str | None = None,
        image_url: str | None = None,
    ) -> tuple[GenerationImage, bool]:
        """
        创建图片记录，利用唯一约束处理并发

        Args:
            task_type: 任务类型 (model/edit/outfit)
            task_id: 关联的任务内部 ID
            angle: 视角
            image_url: 图片 OSS URL

        Returns:
            tuple[GenerationImage, bool]: (图片对象, 是否新创建)
        """
        try:
            image = GenerationImage(
                task_type=task_type,
                task_id=task_id,
                angle=angle,
                image_url=image_url,
            )
            self.session.add(image)
            await self.session.flush()
            await self.session.refresh(image)
            return image, True
        except IntegrityError:
            # 唯一约束冲突，说明已存在
            await self.session.rollback()
            existing = await self.get_by_task(task_type, task_id)
            if existing:
                logger.info(f"Image already exists for task {task_type}:{task_id}")
                return existing, False
            # 理论上不会到这里，但作为防御
            raise

    async def get_by_task(
        self,
        task_type: TaskType,
        task_id: int,
    ) -> GenerationImage | None:
        """
        根据任务类型和任务 ID 获取图片

        Args:
            task_type: 任务类型
            task_id: 任务内部 ID

        Returns:
            图片对象，不存在则返回 None
        """
        result = await self.session.execute(
            select(GenerationImage).where(
                GenerationImage.task_type == task_type,
                GenerationImage.task_id == task_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_all_by_task(
        self,
        task_type: TaskType,
        task_id: int,
    ) -> list[GenerationImage]:
        """
        根据任务类型和任务 ID 获取所有图片

        Args:
            task_type: 任务类型
            task_id: 任务内部 ID

        Returns:
            图片对象列表
        """
        result = await self.session.execute(
            select(GenerationImage).where(
                GenerationImage.task_type == task_type,
                GenerationImage.task_id == task_id,
            )
        )
        return list(result.scalars().all())

    async def get_by_id(self, id: int) -> GenerationImage | None:
        """
        根据图片 ID 获取图片

        Args:
            id: 图片 ID

        Returns:
            图片对象，不存在则返回 None
        """
        result = await self.session.execute(
            select(GenerationImage).where(GenerationImage.id == id)
        )
        return result.scalar_one_or_none()
