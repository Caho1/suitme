"""
BaseTaskRepository - 任务 Repository 泛型基类

提供所有任务 Repository 的通用 CRUD 操作，消除重复代码。
子类只需定义 model 类属性和特定的 create 方法。
"""

from datetime import datetime, timezone
from typing import ClassVar, Generic, TypeVar

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base
from app.models import TaskStatus

T = TypeVar("T", bound=Base)


class BaseTaskRepository(Generic[T]):
    """
    任务 Repository 泛型基类
    
    提供通用的 CRUD 操作：
    - get_by_id: 根据内部 ID 获取任务
    - get_by_task_id: 根据 Apimart task_id 获取任务
    - update_status: 更新任务状态
    - get_pending_tasks: 获取待处理任务
    
    子类必须定义 model 类属性指定具体的模型类。
    """

    model: ClassVar[type[Base]]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: int) -> T | None:
        """
        根据内部数据库 ID 获取任务

        Args:
            id: 数据库自增 ID

        Returns:
            任务对象，不存在则返回 None
        """
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_task_id(self, task_id: str) -> T | None:
        """
        根据 Apimart task_id 获取任务

        Args:
            task_id: Apimart 任务 ID

        Returns:
            任务对象，不存在则返回 None
        """
        result = await self.session.execute(
            select(self.model).where(self.model.task_id == task_id)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress: int | None = None,
        error_message: str | None = None,
    ) -> T | None:
        """
        更新任务状态

        Args:
            task_id: Apimart 任务 ID
            status: 新状态
            progress: 进度百分比
            error_message: 错误信息 (失败时)

        Returns:
            更新后的任务对象，不存在则返回 None
        """
        update_data: dict = {
            "status": status,
            "updated_at": datetime.now(timezone.utc),
        }

        if progress is not None:
            update_data["progress"] = progress

        if error_message is not None:
            update_data["error_message"] = error_message

        if status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            update_data["completed_at"] = datetime.now(timezone.utc)

        await self.session.execute(
            update(self.model)
            .where(self.model.task_id == task_id)
            .values(**update_data)
        )
        await self.session.flush()

        return await self.get_by_task_id(task_id)

    async def get_pending_tasks(self) -> list[T]:
        """
        获取所有待处理的任务（submitted 或 processing 状态）

        Returns:
            待处理任务列表
        """
        result = await self.session.execute(
            select(self.model).where(
                self.model.status.in_([
                    TaskStatus.SUBMITTED,
                    TaskStatus.PROCESSING,
                ])
            )
        )
        return list(result.scalars().all())
