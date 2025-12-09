"""
属性测试：Repository 层数据持久化

使用 hypothesis 进行属性测试，验证数据持久化逻辑的正确性。
更新为使用新的分离任务表结构。
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime

from app.database import init_db, create_all_tables, get_session_factory
from app.models import TaskType, TaskStatus
from app.repositories import (
    BaseModelTaskRepository,
    EditTaskRepository,
    OutfitTaskRepository,
    ImageRepository,
)


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

# 有效的 task_id 策略 (Apimart task_id)
task_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_"),
    min_size=1,
    max_size=60,
)

# 角度策略
angle_strategy = st.sampled_from(["front", "side", "back"])

# 性别策略
gender_strategy = st.sampled_from(["male", "female"])

# 身高策略 (cm)
height_strategy = st.floats(min_value=140.0, max_value=220.0, allow_nan=False)

# 体重策略 (kg)
weight_strategy = st.floats(min_value=30.0, max_value=150.0, allow_nan=False)

# 年龄策略
age_strategy = st.integers(min_value=18, max_value=80)

# 肤色策略
skin_tone_strategy = st.sampled_from(["fair", "medium", "olive", "tan", "dark"])

# 身材类型策略
body_shape_strategy = st.sampled_from(["slim", "athletic", "average", "curvy", None])


# ============== Property 6: 任务创建数据持久化 ==============
# **Feature: database-refactor, Property 6: 任务创建数据持久化**
# **Validates: Requirements 1.1, 2.1, 3.1**


@pytest.mark.asyncio
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    task_id=task_id_strategy,
    request_id=request_id_strategy,
    user_id=user_id_strategy,
    gender=gender_strategy,
    height_cm=height_strategy,
    weight_kg=weight_strategy,
    age=age_strategy,
    skin_tone=skin_tone_strategy,
    body_shape=body_shape_strategy,
)
async def test_base_model_task_creation_persists_data(
    task_id: str,
    request_id: str,
    user_id: str,
    gender: str,
    height_cm: float,
    weight_kg: float,
    age: int,
    skin_tone: str,
    body_shape: str | None,
):
    """
    **Feature: database-refactor, Property 6: 任务创建数据持久化**
    
    *For any* 成功创建的 BaseModelTask，数据库中 SHALL 存在对应记录，
    包含正确的 body_profile 字段和 status="submitted"。
    """
    async with await get_test_session() as session:
        repo = BaseModelTaskRepository(session)
        
        # 创建任务
        task = await repo.create(
            task_id=task_id,
            request_id=request_id,
            user_id=user_id,
            gender=gender,
            height_cm=height_cm,
            weight_kg=weight_kg,
            age=age,
            skin_tone=skin_tone,
            body_shape=body_shape,
        )
        
        # 验证任务已创建
        assert task.id is not None
        assert task.id > 0
        
        # 从数据库重新获取任务
        retrieved_task = await repo.get_by_id(task.id)
        
        # 验证数据持久化正确
        assert retrieved_task is not None
        assert retrieved_task.task_id == task_id
        assert retrieved_task.request_id == request_id
        assert retrieved_task.user_id == user_id
        assert retrieved_task.gender == gender
        assert retrieved_task.height_cm == height_cm
        assert retrieved_task.weight_kg == weight_kg
        assert retrieved_task.age == age
        assert retrieved_task.skin_tone == skin_tone
        assert retrieved_task.body_shape == body_shape
        assert retrieved_task.status == TaskStatus.SUBMITTED
        
        # 回滚以便下次测试
        await session.rollback()


@pytest.mark.asyncio
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    base_task_id=task_id_strategy,
    edit_task_id=task_id_strategy,
    request_id=request_id_strategy,
    user_id=user_id_strategy,
    gender=gender_strategy,
    height_cm=height_strategy,
    weight_kg=weight_strategy,
    age=age_strategy,
    skin_tone=skin_tone_strategy,
    edit_instructions=st.text(min_size=1, max_size=200),
)
async def test_edit_task_with_base_model_reference(
    base_task_id: str,
    edit_task_id: str,
    request_id: str,
    user_id: str,
    gender: str,
    height_cm: float,
    weight_kg: float,
    age: int,
    skin_tone: str,
    edit_instructions: str,
):
    """
    **Feature: database-refactor, Property 6: 任务创建数据持久化**
    
    *For any* EditTask，数据库中 SHALL 正确关联 base_model_id。
    """
    async with await get_test_session() as session:
        base_repo = BaseModelTaskRepository(session)
        edit_repo = EditTaskRepository(session)
        
        # 先创建一个 BaseModelTask 作为基础模特
        base_task = await base_repo.create(
            task_id=base_task_id,
            request_id=f"base-{request_id}",
            user_id=user_id,
            gender=gender,
            height_cm=height_cm,
            weight_kg=weight_kg,
            age=age,
            skin_tone=skin_tone,
        )
        
        # 创建 EditTask
        edit_task = await edit_repo.create(
            task_id=edit_task_id,
            request_id=f"edit-{request_id}",
            user_id=user_id,
            base_model_id=base_task.id,
            edit_instructions=edit_instructions,
        )
        
        # 验证 EditTask 关联正确
        retrieved_edit = await edit_repo.get_by_id(edit_task.id)
        assert retrieved_edit is not None
        assert retrieved_edit.base_model_id == base_task.id
        assert retrieved_edit.edit_instructions == edit_instructions
        assert retrieved_edit.status == TaskStatus.SUBMITTED
        
        # 回滚以便下次测试
        await session.rollback()


@pytest.mark.asyncio
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    base_task_id=task_id_strategy,
    outfit_task_id=task_id_strategy,
    request_id=request_id_strategy,
    user_id=user_id_strategy,
    gender=gender_strategy,
    height_cm=height_strategy,
    weight_kg=weight_strategy,
    age=age_strategy,
    skin_tone=skin_tone_strategy,
    angle=angle_strategy,
    outfit_description=st.text(min_size=0, max_size=200) | st.none(),
)
async def test_outfit_task_with_base_model_reference(
    base_task_id: str,
    outfit_task_id: str,
    request_id: str,
    user_id: str,
    gender: str,
    height_cm: float,
    weight_kg: float,
    age: int,
    skin_tone: str,
    angle: str,
    outfit_description: str | None,
):
    """
    **Feature: database-refactor, Property 6: 任务创建数据持久化**
    
    *For any* OutfitTask，数据库中 SHALL 正确关联 base_model_id 和 angle。
    """
    async with await get_test_session() as session:
        base_repo = BaseModelTaskRepository(session)
        outfit_repo = OutfitTaskRepository(session)
        
        # 先创建一个 BaseModelTask 作为基础模特
        base_task = await base_repo.create(
            task_id=base_task_id,
            request_id=f"base-{request_id}",
            user_id=user_id,
            gender=gender,
            height_cm=height_cm,
            weight_kg=weight_kg,
            age=age,
            skin_tone=skin_tone,
        )
        
        # 创建 OutfitTask
        outfit_task = await outfit_repo.create(
            task_id=outfit_task_id,
            request_id=f"outfit-{request_id}",
            user_id=user_id,
            base_model_id=base_task.id,
            angle=angle,
            outfit_description=outfit_description,
        )
        
        # 验证 OutfitTask 关联正确
        retrieved_outfit = await outfit_repo.get_by_id(outfit_task.id)
        assert retrieved_outfit is not None
        assert retrieved_outfit.base_model_id == base_task.id
        assert retrieved_outfit.angle == angle
        assert retrieved_outfit.outfit_description == outfit_description
        assert retrieved_outfit.status == TaskStatus.SUBMITTED
        
        # 回滚以便下次测试
        await session.rollback()


# ============== Property 12: 任务时间戳正确更新 ==============
# **Feature: database-refactor, Property 12: 任务时间戳正确更新**
# **Validates: Requirements 2.1, 2.2, 2.3**


@pytest.mark.asyncio
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    task_id=task_id_strategy,
    request_id=request_id_strategy,
    user_id=user_id_strategy,
    gender=gender_strategy,
    height_cm=height_strategy,
    weight_kg=weight_strategy,
    age=age_strategy,
    skin_tone=skin_tone_strategy,
    new_status=st.sampled_from([TaskStatus.PROCESSING, TaskStatus.COMPLETED, TaskStatus.FAILED]),
    progress=st.integers(min_value=0, max_value=100),
)
async def test_task_timestamp_updated_on_status_change(
    task_id: str,
    request_id: str,
    user_id: str,
    gender: str,
    height_cm: float,
    weight_kg: float,
    age: int,
    skin_tone: str,
    new_status: TaskStatus,
    progress: int,
):
    """
    **Feature: database-refactor, Property 12: 任务时间戳正确更新**
    
    *For any* 任务状态更新，updated_at 字段 SHALL 被更新。
    """
    async with await get_test_session() as session:
        repo = BaseModelTaskRepository(session)
        
        # 创建任务
        task = await repo.create(
            task_id=task_id,
            request_id=request_id,
            user_id=user_id,
            gender=gender,
            height_cm=height_cm,
            weight_kg=weight_kg,
            age=age,
            skin_tone=skin_tone,
        )
        
        original_updated_at = task.updated_at
        
        # 更新状态
        updated_task = await repo.update_status(
            task_id=task_id,
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
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    task_id=task_id_strategy,
    request_id=request_id_strategy,
    user_id=user_id_strategy,
    gender=gender_strategy,
    height_cm=height_strategy,
    weight_kg=weight_strategy,
    age=age_strategy,
    skin_tone=skin_tone_strategy,
)
async def test_completed_at_set_on_completion(
    task_id: str,
    request_id: str,
    user_id: str,
    gender: str,
    height_cm: float,
    weight_kg: float,
    age: int,
    skin_tone: str,
):
    """
    **Feature: database-refactor, Property 12: 任务时间戳正确更新**
    
    *For any* 任务完成时，completed_at 字段 SHALL 被设置。
    """
    async with await get_test_session() as session:
        repo = BaseModelTaskRepository(session)
        
        # 创建任务
        task = await repo.create(
            task_id=task_id,
            request_id=request_id,
            user_id=user_id,
            gender=gender,
            height_cm=height_cm,
            weight_kg=weight_kg,
            age=age,
            skin_tone=skin_tone,
        )
        
        # 初始状态 completed_at 应为 None
        assert task.completed_at is None
        
        # 更新为 COMPLETED 状态
        completed_task = await repo.update_status(
            task_id=task_id,
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
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    task_id=task_id_strategy,
    request_id=request_id_strategy,
    user_id=user_id_strategy,
    gender=gender_strategy,
    height_cm=height_strategy,
    weight_kg=weight_strategy,
    age=age_strategy,
    skin_tone=skin_tone_strategy,
    error_message=st.text(min_size=1, max_size=200),
)
async def test_completed_at_set_on_failure(
    task_id: str,
    request_id: str,
    user_id: str,
    gender: str,
    height_cm: float,
    weight_kg: float,
    age: int,
    skin_tone: str,
    error_message: str,
):
    """
    **Feature: database-refactor, Property 12: 任务时间戳正确更新**
    
    *For any* 任务失败时，completed_at 字段 SHALL 被设置，error_message 被记录。
    """
    async with await get_test_session() as session:
        repo = BaseModelTaskRepository(session)
        
        # 创建任务
        task = await repo.create(
            task_id=task_id,
            request_id=request_id,
            user_id=user_id,
            gender=gender,
            height_cm=height_cm,
            weight_kg=weight_kg,
            age=age,
            skin_tone=skin_tone,
        )
        
        # 初始状态 completed_at 应为 None
        assert task.completed_at is None
        
        # 更新为 FAILED 状态
        failed_task = await repo.update_status(
            task_id=task_id,
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
