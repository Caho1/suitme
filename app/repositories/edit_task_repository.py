"""
EditTask Repository

数据访问层：模特编辑任务表的 CRUD 操作封装。
继承自 BaseTaskRepository 泛型基类。
"""

from app.models import EditTask, TaskStatus
from app.repositories.base_task_repository import BaseTaskRepository


class EditTaskRepository(BaseTaskRepository[EditTask]):
    """模特编辑任务数据访问仓库"""

    model = EditTask

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
