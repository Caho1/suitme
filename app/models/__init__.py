"""
SQLAlchemy Database Models

定义数据库表结构，包含三种任务类型和图片表。
- BaseModelTask: 模特生成任务
- EditTask: 模特编辑任务
- OutfitTask: 穿搭生成任务
- GenerationImage: 生成图片
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ============== 枚举类型 ==============

class TaskType(str, PyEnum):
    """任务类型枚举"""
    MODEL = "model"
    EDIT = "edit"
    OUTFIT = "outfit"


class TaskStatus(str, PyEnum):
    """任务状态枚举"""
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ============== 数据库模型 ==============

class BaseModelTask(Base):
    """
    模特生成任务表 (F1)
    
    存储根据用户照片和身体参数生成数字模特的任务。
    包含完整的 body_profile 字段。
    """
    __tablename__ = "base_model_task"
    __table_args__ = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(
        String(128), 
        nullable=False, 
        unique=True, 
        index=True,
    )
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    
    # Body profile fields (all optional)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    skin_tone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    body_shape: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Status fields
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False, length=20),
        nullable=False,
        default=TaskStatus.SUBMITTED,
    )
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    edit_tasks: Mapped[list["EditTask"]] = relationship(
        "EditTask",
        back_populates="base_model",
        cascade="all, delete-orphan",
    )
    outfit_tasks: Mapped[list["OutfitTask"]] = relationship(
        "OutfitTask",
        back_populates="base_model",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<BaseModelTask(id={self.id}, task_id={self.task_id}, "
            f"status={self.status}, user_id={self.user_id})>"
        )


class EditTask(Base):
    """
    模特编辑任务表 (F2)
    
    存储在已有模特基础上进行局部调整的任务。
    通过 base_model_id 关联到 BaseModelTask。
    """
    __tablename__ = "edit_task"
    __table_args__ = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(
        String(128), 
        nullable=False, 
        unique=True, 
        index=True,
    )
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    
    # Foreign key to base model
    base_model_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("base_model_task.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Edit specific fields
    edit_instructions: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Status fields
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False, length=20),
        nullable=False,
        default=TaskStatus.SUBMITTED,
    )
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    base_model: Mapped["BaseModelTask"] = relationship(
        "BaseModelTask",
        back_populates="edit_tasks",
    )

    def __repr__(self) -> str:
        return (
            f"<EditTask(id={self.id}, task_id={self.task_id}, "
            f"base_model_id={self.base_model_id}, status={self.status})>"
        )


class OutfitTask(Base):
    """
    穿搭生成任务表 (F3)
    
    存储将服装穿到数字模特上的任务。
    通过 base_model_id 关联到 BaseModelTask。
    """
    __tablename__ = "outfit_task"
    __table_args__ = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(
        String(128), 
        nullable=False, 
        unique=True, 
        index=True,
    )
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    
    # Foreign key to base model
    base_model_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("base_model_task.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Outfit specific fields
    angle: Mapped[str] = mapped_column(String(20), nullable=False)  # front/side/back
    outfit_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Status fields
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False, length=20),
        nullable=False,
        default=TaskStatus.SUBMITTED,
    )
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    base_model: Mapped["BaseModelTask"] = relationship(
        "BaseModelTask",
        back_populates="outfit_tasks",
    )

    def __repr__(self) -> str:
        return (
            f"<OutfitTask(id={self.id}, task_id={self.task_id}, "
            f"base_model_id={self.base_model_id}, angle={self.angle}, status={self.status})>"
        )


class GenerationImage(Base):
    """
    生成图片表
    
    存储任务完成后生成的图片数据。
    使用 task_type 和 task_id 实现多态关联到不同任务表。
    """
    __tablename__ = "generation_image"
    __table_args__ = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Polymorphic reference to task
    task_type: Mapped[str] = mapped_column(
        Enum(TaskType, native_enum=False, length=20),
        nullable=False,
        index=True,
    )
    task_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )
    
    # Image data
    angle: Mapped[str | None] = mapped_column(String(20), nullable=True)
    image_base64: Mapped[str | None] = mapped_column(LONGTEXT, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"<GenerationImage(id={self.id}, task_type={self.task_type}, "
            f"task_id={self.task_id}, angle={self.angle})>"
        )
