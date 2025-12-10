"""
OutfitTask Repository

数据访问层：穿搭生成任务表的 CRUD 操作封装。
继承自 BaseTaskRepository 泛型基类。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OutfitTask, BaseModelTask, TaskStatus
from app.repositories.base_task_repository import BaseTaskRepository


class OutfitTaskRepository(BaseTaskRepository[OutfitTask]):
    """穿搭生成任务数据访问仓库"""

    model = OutfitTask

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def _validate_base_model_exists(self, base_model_id: int) -> bool:
        """
        验证 base_model_id 是否存在

        Args:
            base_model_id: 基础模特任务 ID

        Returns:
            是否存在
        """
        result = await self.session.execute(
            select(BaseModelTask.id).where(BaseModelTask.id == base_model_id)
        )
        return result.scalar_one_or_none() is not None

    async def create(
        self,
        task_id: str,
        request_id: str,
        user_id: str,
        base_model_id: int,
        angle: str,
        outfit_description: str | None = None,
    ) -> OutfitTask:
        """
        创建穿搭生成任务

        Args:
            task_id: Apimart 返回的任务 ID
            request_id: 请求唯一标识
            user_id: 用户 ID
            base_model_id: 关联的基础模特任务 ID
            angle: 视角 (front/side/back)
            outfit_description: 服装描述 (可选)

        Returns:
            创建的任务对象

        Raises:
            ValueError: 当 base_model_id 不存在时
        """
        if not await self._validate_base_model_exists(base_model_id):
            raise ValueError(f"Base model with id {base_model_id} does not exist")

        task = OutfitTask(
            task_id=task_id,
            request_id=request_id,
            user_id=user_id,
            base_model_id=base_model_id,
            angle=angle,
            outfit_description=outfit_description,
            status=TaskStatus.SUBMITTED,
            progress=0,
        )
        self.session.add(task)
        await self.session.flush()
        await self.session.refresh(task)
        return task
