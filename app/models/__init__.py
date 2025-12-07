"""
SQLAlchemy Database Models

定义数据库表结构，包含任务和图片两个核心表。
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ============== 枚举类型 ==============

class TaskType(str, PyEnum):
    """任务类型枚举"""
    DEFAULT = "default"
    EDIT = "edit"
    OUTFIT = "outfit"


class TaskStatus(str, PyEnum):
    """任务状态枚举"""
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ============== 数据库模型 ==============

class AIGenerationTask(Base):
    """
    AI 生成任务表
    
    存储所有生图任务的元数据和状态信息。
    """
    __tablename__ = "ai_generation_task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    external_task_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    type: Mapped[TaskType] = mapped_column(
        Enum(TaskType, native_enum=False, length=20),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    base_model_task_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("ai_generation_task.id"),
        nullable=True,
    )
    angle: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False, length=20),
        nullable=False,
        default=TaskStatus.SUBMITTED,
    )
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
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

    # 关系
    images: Mapped[list["AIGenerationImage"]] = relationship(
        "AIGenerationImage",
        back_populates="task",
        cascade="all, delete-orphan",
    )
    base_model_task: Mapped["AIGenerationTask | None"] = relationship(
        "AIGenerationTask",
        remote_side=[id],
        foreign_keys=[base_model_task_id],
    )

    def __repr__(self) -> str:
        return (
            f"<AIGenerationTask(id={self.id}, type={self.type}, "
            f"status={self.status}, user_id={self.user_id})>"
        )


class AIGenerationImage(Base):
    """
    AI 生成图片表
    
    存储任务完成后生成的图片数据。
    """
    __tablename__ = "ai_generation_image"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ai_generation_task.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    angle: Mapped[str | None] = mapped_column(String(20), nullable=True)
    image_base64: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    # 关系
    task: Mapped["AIGenerationTask"] = relationship(
        "AIGenerationTask",
        back_populates="images",
    )

    def __repr__(self) -> str:
        return (
            f"<AIGenerationImage(id={self.id}, task_id={self.task_id}, "
            f"angle={self.angle})>"
        )
