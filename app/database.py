"""
数据库连接配置模块

使用 SQLAlchemy 2.x 异步模式配置数据库连接。
开发环境使用 aiosqlite，生产环境使用 MySQL。
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""

    pass


# 全局引擎和会话工厂（延迟初始化）
_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """获取数据库引擎"""
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """获取会话工厂"""
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _async_session_factory


def init_db(database_url: str, echo: bool = False) -> None:
    """
    初始化数据库连接

    Args:
        database_url: 数据库连接 URL
        echo: 是否打印 SQL 语句（调试用）
    """
    global _engine, _async_session_factory

    _engine = create_async_engine(
        database_url,
        echo=echo,
        pool_pre_ping=True,
    )

    _async_session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def close_db() -> None:
    """关闭数据库连接"""
    global _engine, _async_session_factory

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话（用于 FastAPI 依赖注入）

    Yields:
        AsyncSession: 数据库会话
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_db_session_context() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话（上下文管理器版本，用于非 FastAPI 场景）

    Yields:
        AsyncSession: 数据库会话
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_all_tables() -> None:
    """创建所有数据库表"""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_all_tables() -> None:
    """删除所有数据库表（仅用于测试）"""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
