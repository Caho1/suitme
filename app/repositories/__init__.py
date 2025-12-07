"""
Repository Layer

数据访问层：封装数据库 CRUD 操作。
"""

from app.repositories.task_repository import TaskRepository
from app.repositories.image_repository import ImageRepository

__all__ = [
    "TaskRepository",
    "ImageRepository",
]
