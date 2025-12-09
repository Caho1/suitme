"""
EditTask Repository

数据访问层：模特编辑任务表的 CRUD 操作封装。
"""

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EditTask, BaseModelTask, TaskStatus


class EditTaskRepository:
    """模特编辑任务数据访问仓库"""

    def __init__(self, session: AsyncSession):
        self.session = session

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
        edit_instructions: str,
    ) -> EditTask:
        """
        创建模特编辑任务

        Args:
            task_id: Apimart 返回的任务 ID
            request_id: 请求唯一标识
            user_id: 用户 ID
            base_model_id: 关联的基础模特任务 ID
            edit_instructions: 编辑指令

        Returns:
            创建的任务对象

        Raises:
            ValueError: 当 base_model_id 不存在时
        """
        if not await self._validate_base_model_exists(base_model_id):
            raise ValueError(f"Base model with id {base_model_id} does not exist")

        task = EditTask(
            task_id=task_id,
            request_id=request_id,
            user_id=user_id,
            base_model_id=base_model_id,
            edit_instructions=edit_instructions,
            status=TaskStatus.SUBMITTED,
            progress=0,
        )
        self.session.add(task)
        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def get_by_id(self, id: int) -> EditTask | None:
        """
        根据内部数据库 ID 获取任务

        Args:
            id: 数据库自增 ID

        Returns:
            任务对象，不存在则返回 None
        """
        result = await self.session.execute(
            select(EditTask).where(EditTask.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_task_id(self, task_id: str) -> EditTask | None:
        """
        根据 Apimart task_id 获取任务

        Args:
            task_id: Apimart 任务 ID

        Returns:
            任务对象，不存在则返回 None
        """
        result = await self.session.execute(
            select(EditTask).where(EditTask.task_id == task_id)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress: int | None = None,
        error_message: str | None = None,
    ) -> EditTask | None:
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
            update(EditTask)
            .where(EditTask.task_id == task_id)
            .values(**update_data)
        )
        await self.session.flush()

        return await self.get_by_task_id(task_id)

    async def get_pending_tasks(self) -> list[EditTask]:
        """
        获取所有待处理的任务（submitted 或 processing 状态）

        Returns:
            待处理任务列表
        """
        result = await self.session.execute(
            select(EditTask).where(
                EditTask.status.in_([
                    TaskStatus.SUBMITTED,
                    TaskStatus.PROCESSING,
                ])
            )
        )
        return list(result.scalars().all())
