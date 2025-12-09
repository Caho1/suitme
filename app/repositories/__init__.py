"""
Repository Layer

数据访问层：封装数据库 CRUD 操作。
"""

from app.repositories.base_model_task_repository import BaseModelTaskRepository
from app.repositories.edit_task_repository import EditTaskRepository
from app.repositories.outfit_task_repository import OutfitTaskRepository
from app.repositories.image_repository import ImageRepository

__all__ = [
    "BaseModelTaskRepository",
    "EditTaskRepository",
    "OutfitTaskRepository",
    "ImageRepository",
]
