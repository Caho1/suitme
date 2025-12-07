"""
Task Repository

数据访问层：任务表的 CRUD 操作封装。
"""

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AIGenerationTask, TaskStatus, TaskType


class TaskRepository:
    """任务数据访问仓库"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        request_id: str,
        user_id: str,
        task_type: TaskType,
        base_model_task_id: int | None = None,
        angle: str | None = None,
        external_task_id: str | None = None,
    ) -> AIGenerationTask:
        """
        创建新任务

        Args:
            request_id: 请求唯一标识
            user_id: 用户 ID
            task_type: 任务类型
            base_model_task_id: 基础模特任务 ID (edit/outfit 任务需要)
            angle: 视角 (outfit 任务需要)
            external_task_id: Apimart 外部任务 ID

        Returns:
            创建的任务对象
        """
        task = AIGenerationTask(
            request_id=request_id,
            user_id=user_id,
            type=task_type,
            base_model_task_id=base_model_task_id,
            angle=angle,
            external_task_id=external_task_id,
            status=TaskStatus.SUBMITTED,
            progress=0,
        )
        self.session.add(task)
        await self.session.flush()
        await self.session.refresh(task)
        return task


    async def get_by_id(self, task_id: int) -> AIGenerationTask | None:
        """
        根据 ID 获取任务

        Args:
            task_id: 任务 ID

        Returns:
            任务对象，不存在则返回 None
        """
        result = await self.session.execute(
            select(AIGenerationTask).where(AIGenerationTask.id == task_id)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        task_id: int,
        status: TaskStatus,
        progress: int | None = None,
        error_message: str | None = None,
    ) -> AIGenerationTask | None:
        """
        更新任务状态

        Args:
            task_id: 任务 ID
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

        # 任务完成或失败时设置 completed_at
        if status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            update_data["completed_at"] = datetime.now(timezone.utc)

        await self.session.execute(
            update(AIGenerationTask)
            .where(AIGenerationTask.id == task_id)
            .values(**update_data)
        )
        await self.session.flush()

        return await self.get_by_id(task_id)

    async def get_pending_tasks(self) -> list[AIGenerationTask]:
        """
        获取所有待处理的任务（submitted 或 processing 状态）

        Returns:
            待处理任务列表
        """
        result = await self.session.execute(
            select(AIGenerationTask).where(
                AIGenerationTask.status.in_([
                    TaskStatus.SUBMITTED,
                    TaskStatus.PROCESSING,
                ])
            )
        )
        return list(result.scalars().all())

    async def set_external_task_id(
        self,
        task_id: int,
        external_task_id: str,
    ) -> AIGenerationTask | None:
        """
        设置外部任务 ID

        Args:
            task_id: 任务 ID
            external_task_id: Apimart 外部任务 ID

        Returns:
            更新后的任务对象
        """
        await self.session.execute(
            update(AIGenerationTask)
            .where(AIGenerationTask.id == task_id)
            .values(
                external_task_id=external_task_id,
                updated_at=datetime.now(timezone.utc),
            )
        )
        await self.session.flush()
        return await self.get_by_id(task_id)
