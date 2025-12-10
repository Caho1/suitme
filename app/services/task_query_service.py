"""
Task Query Service

业务逻辑层：统一的任务查询服务。
在三个任务表中搜索任务，返回一致的响应格式。
"""

from dataclasses import dataclass
from typing import Union

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    BaseModelTask,
    EditTask,
    OutfitTask,
    TaskStatus,
    TaskType,
)
from app.repositories import (
    BaseModelTaskRepository,
    BaseTaskRepository,
    EditTaskRepository,
    OutfitTaskRepository,
)


@dataclass
class TaskQueryResult:
    """
    任务查询结果
    
    统一的任务查询返回格式，包含任务对象和任务类型。
    """
    task: Union[BaseModelTask, EditTask, OutfitTask]
    task_type: TaskType
    
    @property
    def id(self) -> int:
        """任务内部数据库 ID"""
        return self.task.id
    
    @property
    def task_id(self) -> str:
        """Apimart 任务 ID"""
        return self.task.task_id
    
    @property
    def status(self) -> TaskStatus:
        """任务状态"""
        return self.task.status
    
    @property
    def progress(self) -> int:
        """任务进度"""
        return self.task.progress
    
    @property
    def error_message(self) -> str | None:
        """错误信息"""
        return self.task.error_message
    
    @property
    def angle(self) -> str | None:
        """视角（仅 outfit 任务有）"""
        return getattr(self.task, 'angle', None)


class TaskQueryService:
    """
    统一任务查询服务
    
    在三个任务表（base_model_task, edit_task, outfit_task）中
    搜索任务，返回一致的响应格式。
    
    Requirements: 3.4
    """

    def __init__(self, session: AsyncSession):
        """
        初始化任务查询服务

        Args:
            session: 数据库会话
        """
        self.session = session
        self.base_model_repo = BaseModelTaskRepository(session)
        self.edit_repo = EditTaskRepository(session)
        self.outfit_repo = OutfitTaskRepository(session)

    async def find_by_task_id(self, task_id: str) -> TaskQueryResult | None:
        """
        根据 Apimart task_id 在所有表中查找任务
        
        按顺序在 base_model_task、edit_task、outfit_task 表中查找，
        返回第一个匹配的任务。

        Args:
            task_id: Apimart 任务 ID (格式: task_xxxxxxx)

        Returns:
            TaskQueryResult 包含任务对象和类型，未找到返回 None
            
        Requirements: 3.4
        """
        # 先在 base_model_task 表中查找
        task = await self.base_model_repo.get_by_task_id(task_id)
        if task:
            return TaskQueryResult(task=task, task_type=TaskType.MODEL)
        
        # 再在 edit_task 表中查找
        task = await self.edit_repo.get_by_task_id(task_id)
        if task:
            return TaskQueryResult(task=task, task_type=TaskType.EDIT)
        
        # 最后在 outfit_task 表中查找
        task = await self.outfit_repo.get_by_task_id(task_id)
        if task:
            return TaskQueryResult(task=task, task_type=TaskType.OUTFIT)
        
        return None

    async def exists(self, task_id: str) -> bool:
        """
        检查任务是否存在

        Args:
            task_id: Apimart 任务 ID

        Returns:
            任务是否存在
        """
        result = await self.find_by_task_id(task_id)
        return result is not None

    def _get_repo_by_type(self, task_type: TaskType) -> BaseTaskRepository:
        """
        根据任务类型返回对应的 repository
        
        Args:
            task_type: 任务类型 (MODEL, EDIT, OUTFIT)
            
        Returns:
            对应的 repository 实例
            
        Requirements: 1.2
        """
        repo_map = {
            TaskType.MODEL: self.base_model_repo,
            TaskType.EDIT: self.edit_repo,
            TaskType.OUTFIT: self.outfit_repo,
        }
        return repo_map[task_type]

    async def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress: int | None = None,
        error_message: str | None = None,
    ) -> TaskQueryResult | None:
        """
        统一的任务状态更新方法
        
        查找任务、确定类型、调用对应 repository 的 update_status。
        任务不存在时返回 None。
        
        Args:
            task_id: Apimart 任务 ID
            status: 新状态
            progress: 进度百分比
            error_message: 错误信息 (失败时)
            
        Returns:
            TaskQueryResult 包含更新后的任务对象和类型，未找到返回 None
            
        Requirements: 1.1, 1.3, 1.4
        """
        # 先查找任务以确定类型
        query_result = await self.find_by_task_id(task_id)
        if query_result is None:
            return None
        
        # 根据类型获取对应的 repository 并更新
        repo = self._get_repo_by_type(query_result.task_type)
        updated_task = await repo.update_status(
            task_id=task_id,
            status=status,
            progress=progress,
            error_message=error_message,
        )
        
        if updated_task is None:
            return None
        
        return TaskQueryResult(task=updated_task, task_type=query_result.task_type)
