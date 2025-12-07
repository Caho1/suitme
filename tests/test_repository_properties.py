"""
属性测试：Repository 层数据持久化

使用 hypothesis 进行属性测试，验证数据持久化逻辑的正确性。
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime

from app.database import init_db, close_db, create_all_tables, drop_all_tables, get_session_factory
from app.models import TaskType, TaskStatus
from app.repositories import TaskRepository, ImageRepository


# ============== 数据库上下文管理 ==============

_db_initialized = False


async def ensure_db_initialized():
    """确保数据库已初始化"""
    global _db_initialized
    if not _db_initialized:
        init_db("sqlite+aiosqlite:///:memory:", echo=False)
        await create_all_tables()
        _db_initialized = True


async def get_test_session():
    """获取测试数据库会话"""
    await ensure_db_initialized()
    session_factory = get_session_factory()
    return session_factory()


# ============== 测试策略 ==============

# 有效的 request_id 策略
request_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_"),
    min_size=1,
    max_size=60,
)

# 有效的 user_id 策略
user_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_"),
    min_size=1,
    max_size=60,
)

# 任务类型策略
task_type_strategy = st.sampled_from([TaskType.DEFAULT, TaskType.EDIT, TaskType.OUTFIT])

# 角度策略
angle_strategy = st.sampled_from(["front", "side", "back", None])


# ============== Property 6: 任务创建数据持久化 ==============
# **Feature: suitme-image-generation, Property 6: 任务创建数据持久化**
# **Validates: Requirements 1.4, 2.3, 3.4, 8.1**


@pytest.mark.asyncio
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    request_id=request_id_strategy,
    user_id=user_id_strategy,
    task_type=task_type_strategy,
    angle=angle_strategy,
)
async def test_task_creation_persists_data(
    request_id: str,
    user_id: str,
    task_type: TaskType,
    angle: str | None,
):
    """
    **Feature: suitme-image-generation, Property 6: 任务创建数据持久化**
    
    *For any* 成功创建的任务，数据库中 SHALL 存在对应记录，
    包含正确的 request_id、type、user_id、status="submitted"。
    """
    async with await get_test_session() as session:
        repo = TaskRepository(session)
        
        # 创建任务
        task = await repo.create(
            request_id=request_id,
            user_id=user_id,
            task_type=task_type,
            angle=angle if task_type == TaskType.OUTFIT else None,
        )
        
        # 验证任务已创建
        assert task.id is not None
        assert task.id > 0
        
        # 从数据库重新获取任务
        retrieved_task = await repo.get_by_id(task.id)
        
        # 验证数据持久化正确
        assert retrieved_task is not None
        assert retrieved_task.request_id == request_id
        assert retrieved_task.user_id == user_id
        assert retrieved_task.type == task_type
        assert retrieved_task.status == TaskStatus.SUBMITTED
        
        # outfit 任务验证 angle
        if task_type == TaskType.OUTFIT:
            assert retrieved_task.angle == angle
        
        # 回滚以便下次测试
        await session.rollback()


@pytest.mark.asyncio
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    request_id=request_id_strategy,
    user_id=user_id_strategy,
    angle=angle_strategy,
)
async def test_edit_outfit_task_with_base_model_task_id(
    request_id: str,
    user_id: str,
    angle: str | None,
):
    """
    **Feature: suitme-image-generation, Property 6: 任务创建数据持久化**
    
    *For any* edit/outfit 任务，数据库中 SHALL 正确关联 base_model_task_id。
    """
    async with await get_test_session() as session:
        repo = TaskRepository(session)
        
        # 先创建一个 default 任务作为基础模特
        base_task = await repo.create(
            request_id=f"base-{request_id}",
            user_id=user_id,
            task_type=TaskType.DEFAULT,
        )
        
        # 创建 edit 任务
        edit_task = await repo.create(
            request_id=f"edit-{request_id}",
            user_id=user_id,
            task_type=TaskType.EDIT,
            base_model_task_id=base_task.id,
        )
        
        # 验证 edit 任务关联正确
        retrieved_edit = await repo.get_by_id(edit_task.id)
        assert retrieved_edit is not None
        assert retrieved_edit.base_model_task_id == base_task.id
        assert retrieved_edit.type == TaskType.EDIT
        assert retrieved_edit.status == TaskStatus.SUBMITTED
        
        # 创建 outfit 任务
        outfit_task = await repo.create(
            request_id=f"outfit-{request_id}",
            user_id=user_id,
            task_type=TaskType.OUTFIT,
            base_model_task_id=base_task.id,
            angle=angle or "front",
        )
        
        # 验证 outfit 任务关联正确
        retrieved_outfit = await repo.get_by_id(outfit_task.id)
        assert retrieved_outfit is not None
        assert retrieved_outfit.base_model_task_id == base_task.id
        assert retrieved_outfit.type == TaskType.OUTFIT
        assert retrieved_outfit.status == TaskStatus.SUBMITTED
        assert retrieved_outfit.angle == (angle or "front")
        
        # 回滚以便下次测试
        await session.rollback()



# ============== Property 12: 任务时间戳正确更新 ==============
# **Feature: suitme-image-generation, Property 12: 任务时间戳正确更新**
# **Validates: Requirements 8.3, 8.4**


@pytest.mark.asyncio
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    request_id=request_id_strategy,
    user_id=user_id_strategy,
    new_status=st.sampled_from([TaskStatus.PROCESSING, TaskStatus.COMPLETED, TaskStatus.FAILED]),
    progress=st.integers(min_value=0, max_value=100),
)
async def test_task_timestamp_updated_on_status_change(
    request_id: str,
    user_id: str,
    new_status: TaskStatus,
    progress: int,
):
    """
    **Feature: suitme-image-generation, Property 12: 任务时间戳正确更新**
    
    *For any* 任务状态更新，updated_at 字段 SHALL 被更新。
    """
    async with await get_test_session() as session:
        repo = TaskRepository(session)
        
        # 创建任务
        task = await repo.create(
            request_id=request_id,
            user_id=user_id,
            task_type=TaskType.DEFAULT,
        )
        
        original_updated_at = task.updated_at
        
        # 更新状态
        updated_task = await repo.update_status(
            task_id=task.id,
            status=new_status,
            progress=progress,
        )
        
        # 验证 updated_at 已更新
        assert updated_task is not None
        # 比较时移除时区信息（SQLite 返回 naive datetime，更新后是 aware datetime）
        updated_at = updated_task.updated_at.replace(tzinfo=None) if updated_task.updated_at.tzinfo else updated_task.updated_at
        original_at = original_updated_at.replace(tzinfo=None) if original_updated_at and original_updated_at.tzinfo else original_updated_at
        assert updated_at >= original_at
        assert updated_task.status == new_status
        assert updated_task.progress == progress
        
        # 回滚以便下次测试
        await session.rollback()


@pytest.mark.asyncio
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    request_id=request_id_strategy,
    user_id=user_id_strategy,
)
async def test_completed_at_set_on_completion(
    request_id: str,
    user_id: str,
):
    """
    **Feature: suitme-image-generation, Property 12: 任务时间戳正确更新**
    
    *For any* 任务完成时，completed_at 字段 SHALL 被设置。
    """
    async with await get_test_session() as session:
        repo = TaskRepository(session)
        
        # 创建任务
        task = await repo.create(
            request_id=request_id,
            user_id=user_id,
            task_type=TaskType.DEFAULT,
        )
        
        # 初始状态 completed_at 应为 None
        assert task.completed_at is None
        
        # 更新为 COMPLETED 状态
        completed_task = await repo.update_status(
            task_id=task.id,
            status=TaskStatus.COMPLETED,
            progress=100,
        )
        
        # 验证 completed_at 已设置
        assert completed_task is not None
        assert completed_task.completed_at is not None
        assert isinstance(completed_task.completed_at, datetime)
        assert completed_task.status == TaskStatus.COMPLETED
        
        # 回滚以便下次测试
        await session.rollback()


@pytest.mark.asyncio
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    request_id=request_id_strategy,
    user_id=user_id_strategy,
    error_message=st.text(min_size=1, max_size=200),
)
async def test_completed_at_set_on_failure(
    request_id: str,
    user_id: str,
    error_message: str,
):
    """
    **Feature: suitme-image-generation, Property 12: 任务时间戳正确更新**
    
    *For any* 任务失败时，completed_at 字段 SHALL 被设置，error_message 被记录。
    """
    async with await get_test_session() as session:
        repo = TaskRepository(session)
        
        # 创建任务
        task = await repo.create(
            request_id=request_id,
            user_id=user_id,
            task_type=TaskType.DEFAULT,
        )
        
        # 初始状态 completed_at 应为 None
        assert task.completed_at is None
        
        # 更新为 FAILED 状态
        failed_task = await repo.update_status(
            task_id=task.id,
            status=TaskStatus.FAILED,
            error_message=error_message,
        )
        
        # 验证 completed_at 已设置
        assert failed_task is not None
        assert failed_task.completed_at is not None
        assert isinstance(failed_task.completed_at, datetime)
        assert failed_task.status == TaskStatus.FAILED
        assert failed_task.error_message == error_message
        
        # 回滚以便下次测试
        await session.rollback()
