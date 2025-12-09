"""
BaseModelTask Repository

数据访问层：模特生成任务表的 CRUD 操作封装。
"""

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BaseModelTask, TaskStatus


class BaseModelTaskRepository:
    """模特生成任务数据访问仓库"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        task_id: str,
        request_id: str,
        user_id: str,
        gender: str,
        height_cm: float,
        weight_kg: float,
        age: int,
        skin_tone: str,
        body_shape: str | None = None,
    ) -> BaseModelTask:
        """
        创建模特生成任务

        Args:
            task_id: Apimart 返回的任务 ID
            request_id: 请求唯一标识
            user_id: 用户 ID
            gender: 性别
            height_cm: 身高 (cm)
            weight_kg: 体重 (kg)
            age: 年龄
            skin_tone: 肤色
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

    async def get_by_id(self, id: int) -> BaseModelTask | None:
        """
        根据内部数据库 ID 获取任务

        Args:
            id: 数据库自增 ID

        Returns:
            任务对象，不存在则返回 None
        """
        result = await self.session.execute(
            select(BaseModelTask).where(BaseModelTask.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_task_id(self, task_id: str) -> BaseModelTask | None:
        """
        根据 Apimart task_id 获取任务

        Args:
            task_id: Apimart 任务 ID

        Returns:
            任务对象，不存在则返回 None
        """
        result = await self.session.execute(
            select(BaseModelTask).where(BaseModelTask.task_id == task_id)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress: int | None = None,
        error_message: str | None = None,
    ) -> BaseModelTask | None:
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
            update(BaseModelTask)
            .where(BaseModelTask.task_id == task_id)
            .values(**update_data)
        )
        await self.session.flush()

        return await self.get_by_task_id(task_id)

    async def get_pending_tasks(self) -> list[BaseModelTask]:
        """
        获取所有待处理的任务（submitted 或 processing 状态）

        Returns:
            待处理任务列表
        """
        result = await self.session.execute(
            select(BaseModelTask).where(
                BaseModelTask.status.in_([
                    TaskStatus.SUBMITTED,
                    TaskStatus.PROCESSING,
                ])
            )
        )
        return list(result.scalars().all())
