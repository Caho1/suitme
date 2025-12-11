"""
BaseModelTask Repository

数据访问层：模特生成任务表的 CRUD 操作封装。
继承自 BaseTaskRepository 泛型基类。
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BaseModelTask, TaskStatus
from app.repositories.base_task_repository import BaseTaskRepository


class BaseModelTaskRepository(BaseTaskRepository[BaseModelTask]):
    """模特生成任务数据访问仓库"""

    model = BaseModelTask

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def create(
        self,
        task_id: str,
        request_id: str,
        user_id: str,
        gender: str | None = None,
        height_cm: float | None = None,
        weight_kg: float | None = None,
        age: int | None = None,
        skin_tone: str | None = None,
        body_shape: str | None = None,
    ) -> BaseModelTask:
        """
        创建模特生成任务

        Args:
            task_id: Apimart 返回的任务 ID
            request_id: 请求唯一标识
            user_id: 用户 ID
            gender: 性别 (可选)
            height_cm: 身高 (cm) (可选)
            weight_kg: 体重 (kg) (可选)
            age: 年龄 (可选)
            skin_tone: 肤色 (可选)
            body_shape: 身材类型 (可选)

        Returns:
            创建的任务对象
        """
        task = BaseModelTask(
            task_id=task_id,
            request_id=request_id,
            user_id=user_id,
            gender=gender,
            height_cm=height_cm,
            weight_kg=weight_kg,
            age=age,
            skin_tone=skin_tone,
            body_shape=body_shape,
            status=TaskStatus.SUBMITTED,
            progress=0,
        )
        self.session.add(task)
        await self.session.flush()
        await self.session.refresh(task)
        return task
