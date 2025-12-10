"""
属性测试：Service 层业务逻辑

使用 hypothesis 进行属性测试，验证 Service 层的业务逻辑正确性。
"""

import os
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import AsyncMock, MagicMock

from app.database import init_db, create_all_tables, get_session_factory
from app.models import TaskType, TaskStatus
from app.repositories import BaseModelTaskRepository, EditTaskRepository, OutfitTaskRepository, ImageRepository
from app.services.model_service import ModelService, BaseModelNotFoundError
from app.schemas import EditModelRequest, OutfitModelRequest, AngleType


# ============== 数据库上下文管理 ==============

_db_initialized = False


async def ensure_db_initialized():
    """确保数据库已初始化（使用 .env 中配置的数据库）"""
    global _db_initialized
    if not _db_initialized:
        database_url = os.getenv(
            "DATABASE_URL",
            "mysql+aiomysql://root:123456@localhost:3306/suitme"
        )
        init_db(database_url, echo=False)
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

# 不存在的 task_id 策略（使用大的随机正整数，不太可能存在于数据库中）
nonexistent_task_id_strategy = st.integers(min_value=100000, max_value=999999)

# 角度策略
angle_strategy = st.sampled_from([AngleType.FRONT, AngleType.SIDE, AngleType.BACK])

# 编辑指令策略
edit_instructions_strategy = st.text(min_size=1, max_size=200)

# 有效的 Data URI 策略（简化版，用于测试）
# 使用一个最小的有效 1x1 PNG 图片的 Base64
VALID_DATA_URI = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


# ============== Property 4: 无效 base_model_task_id 拒绝 ==============
# **Feature: suitme-image-generation, Property 4: 无效 base_model_task_id 拒绝**
# **Validates: Requirements 2.2, 3.3**


@pytest.mark.asyncio
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    request_id=request_id_strategy,
    user_id=user_id_strategy,
    nonexistent_task_id=nonexistent_task_id_strategy,
    edit_instructions=edit_instructions_strategy,
)
async def test_edit_model_rejects_nonexistent_base_model_task_id(
    request_id: str,
    user_id: str,
    nonexistent_task_id: int,
    edit_instructions: str,
):
    """
    **Feature: suitme-image-generation, Property 4: 无效 base_model_task_id 拒绝**
    
    *For any* 不存在于数据库中的 base_model_task_id，
    edit 请求 SHALL 抛出 BaseModelNotFoundError。
    """
    async with await get_test_session() as session:
        # 创建 mock 的 Apimart 客户端（不应该被调用）
        mock_apimart = AsyncMock()
        
        service = ModelService(session, apimart_client=mock_apimart)
        
        # 构建请求（使用字符串 task_id）
        nonexistent_task_id_str = f"task_{nonexistent_task_id}"
        request = EditModelRequest(
            request_id=request_id,
            user_id=user_id,
            base_model_task_id=nonexistent_task_id_str,
            edit_instructions=edit_instructions,
        )
        
        # 验证抛出 BaseModelNotFoundError
        with pytest.raises(BaseModelNotFoundError) as exc_info:
            await service.edit_model(request)
        
        assert exc_info.value.task_id == nonexistent_task_id_str
        
        # 验证 Apimart 客户端未被调用
        mock_apimart.submit_generation.assert_not_called()
        
        # 回滚以便下次测试
        await session.rollback()


@pytest.mark.asyncio
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    request_id=request_id_strategy,
    user_id=user_id_strategy,
    nonexistent_task_id=nonexistent_task_id_strategy,
    angle=angle_strategy,
)
async def test_outfit_rejects_nonexistent_base_model_task_id(
    request_id: str,
    user_id: str,
    nonexistent_task_id: int,
    angle: AngleType,
):
    """
    **Feature: suitme-image-generation, Property 4: 无效 base_model_task_id 拒绝**
    
    *For any* 不存在于数据库中的 base_model_task_id，
    outfit 请求 SHALL 抛出 BaseModelNotFoundError。
    """
    async with await get_test_session() as session:
        # 创建 mock 的 Apimart 客户端（不应该被调用）
        mock_apimart = AsyncMock()
        
        service = ModelService(session, apimart_client=mock_apimart)
        
        # 构建请求（使用字符串 task_id）
        nonexistent_task_id_str = f"task_{nonexistent_task_id}"
        request = OutfitModelRequest(
            request_id=request_id,
            user_id=user_id,
            base_model_task_id=nonexistent_task_id_str,
            angle=angle,
            outfit_image_urls=["https://example.com/outfit.jpg"],
        )
        
        # 验证抛出 BaseModelNotFoundError
        with pytest.raises(BaseModelNotFoundError) as exc_info:
            await service.create_outfit(request)
        
        assert exc_info.value.task_id == nonexistent_task_id_str
        
        # 验证 Apimart 客户端未被调用
        mock_apimart.submit_generation.assert_not_called()
        
        # 回滚以便下次测试
        await session.rollback()



# ============== Property 7: 任务状态转换正确性 ==============
# **Feature: suitme-image-generation, Property 7: 任务状态转换正确性**
# **Validates: Requirements 4.1, 4.2, 4.3, 4.4**

from app.services.task_service import (
    TaskService,
    TaskNotFoundError,
    InvalidStatusTransitionError,
)


# 有效的状态转换
VALID_TRANSITIONS = {
    TaskStatus.SUBMITTED: {TaskStatus.PROCESSING, TaskStatus.FAILED},
    TaskStatus.PROCESSING: {TaskStatus.COMPLETED, TaskStatus.FAILED},
    TaskStatus.COMPLETED: set(),
    TaskStatus.FAILED: set(),
}

# 所有可能的状态
ALL_STATUSES = [TaskStatus.SUBMITTED, TaskStatus.PROCESSING, TaskStatus.COMPLETED, TaskStatus.FAILED]


@pytest.mark.asyncio
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    request_id=request_id_strategy,
    user_id=user_id_strategy,
)
async def test_valid_status_transition_submitted_to_processing(
    request_id: str,
    user_id: str,
):
    """
    **Feature: suitme-image-generation, Property 7: 任务状态转换正确性**
    
    *For any* 任务，状态转换 submitted → processing SHALL 成功。
    """
    async with await get_test_session() as session:
        task_repo = BaseModelTaskRepository(session)
        task_service = TaskService(session)
        
        # 创建任务（初始状态为 SUBMITTED）
        task_id = f"task_{request_id}"
        task = await task_repo.create(
            task_id=task_id,
            request_id=request_id,
            user_id=user_id,
            gender="male",
            height_cm=175.0,
            weight_kg=70.0,
            age=25,
            skin_tone="light",
        )
        
        # 验证初始状态
        assert task.status == TaskStatus.SUBMITTED
        
        # 转换到 PROCESSING
        await task_service.update_task_status(task_id, TaskStatus.PROCESSING, progress=50)
        
        # 验证状态已更新
        updated_task = await task_repo.get_by_task_id(task_id)
        assert updated_task is not None
        assert updated_task.status == TaskStatus.PROCESSING
        assert updated_task.progress == 50
        
        await session.rollback()


@pytest.mark.asyncio
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    request_id=request_id_strategy,
    user_id=user_id_strategy,
)
async def test_valid_status_transition_processing_to_completed(
    request_id: str,
    user_id: str,
):
    """
    **Feature: suitme-image-generation, Property 7: 任务状态转换正确性**
    
    *For any* 任务，状态转换 processing → completed SHALL 成功。
    """
    async with await get_test_session() as session:
        task_repo = BaseModelTaskRepository(session)
        task_service = TaskService(session)
        
        # 创建任务并转换到 PROCESSING
        task_id = f"task_{request_id}"
        task = await task_repo.create(
            task_id=task_id,
            request_id=request_id,
            user_id=user_id,
            gender="male",
            height_cm=175.0,
            weight_kg=70.0,
            age=25,
            skin_tone="light",
        )
        await task_repo.update_status(task_id, TaskStatus.PROCESSING, progress=50)
        
        # 完成任务
        await task_service.complete_task(
            task_id,
            image_base64="test_base64_data",
        )
        
        # 验证状态已更新
        updated_task = await task_repo.get_by_task_id(task_id)
        assert updated_task is not None
        assert updated_task.status == TaskStatus.COMPLETED
        assert updated_task.progress == 100
        assert updated_task.completed_at is not None
        
        await session.rollback()


@pytest.mark.asyncio
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    request_id=request_id_strategy,
    user_id=user_id_strategy,
    error_message=st.text(min_size=1, max_size=200),
)
async def test_valid_status_transition_to_failed(
    request_id: str,
    user_id: str,
    error_message: str,
):
    """
    **Feature: suitme-image-generation, Property 7: 任务状态转换正确性**
    
    *For any* 任务，状态转换 submitted/processing → failed SHALL 成功。
    """
    async with await get_test_session() as session:
        task_repo = BaseModelTaskRepository(session)
        task_service = TaskService(session)
        
        # 测试从 SUBMITTED 转换到 FAILED
        task_id1 = f"task_fail1_{request_id}"
        task1 = await task_repo.create(
            task_id=task_id1,
            request_id=f"fail1-{request_id}",
            user_id=user_id,
            gender="male",
            height_cm=175.0,
            weight_kg=70.0,
            age=25,
            skin_tone="light",
        )
        
        await task_service.fail_task(task_id1, error_message)
        
        updated_task1 = await task_repo.get_by_task_id(task_id1)
        assert updated_task1 is not None
        assert updated_task1.status == TaskStatus.FAILED
        assert updated_task1.error_message == error_message
        
        # 测试从 PROCESSING 转换到 FAILED
        task_id2 = f"task_fail2_{request_id}"
        task2 = await task_repo.create(
            task_id=task_id2,
            request_id=f"fail2-{request_id}",
            user_id=user_id,
            gender="male",
            height_cm=175.0,
            weight_kg=70.0,
            age=25,
            skin_tone="light",
        )
        await task_repo.update_status(task_id2, TaskStatus.PROCESSING)
        
        await task_service.fail_task(task_id2, error_message)
        
        updated_task2 = await task_repo.get_by_task_id(task_id2)
        assert updated_task2 is not None
        assert updated_task2.status == TaskStatus.FAILED
        
        await session.rollback()


@pytest.mark.asyncio
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    request_id=request_id_strategy,
    user_id=user_id_strategy,
)
async def test_invalid_status_transition_skip_processing(
    request_id: str,
    user_id: str,
):
    """
    **Feature: suitme-image-generation, Property 7: 任务状态转换正确性**
    
    *For any* 任务，不允许跳过中间状态：submitted → completed SHALL 失败。
    """
    async with await get_test_session() as session:
        task_repo = BaseModelTaskRepository(session)
        task_service = TaskService(session)
        
        # 创建任务（初始状态为 SUBMITTED）
        task_id = f"task_{request_id}"
        task = await task_repo.create(
            task_id=task_id,
            request_id=request_id,
            user_id=user_id,
            gender="male",
            height_cm=175.0,
            weight_kg=70.0,
            age=25,
            skin_tone="light",
        )
        
        # 尝试直接跳到 COMPLETED（应该失败）
        with pytest.raises(InvalidStatusTransitionError) as exc_info:
            await task_service.complete_task(task_id, image_base64="test")
        
        assert exc_info.value.current_status == TaskStatus.SUBMITTED
        assert exc_info.value.target_status == TaskStatus.COMPLETED
        
        await session.rollback()


@pytest.mark.asyncio
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    request_id=request_id_strategy,
    user_id=user_id_strategy,
)
async def test_invalid_status_transition_reverse(
    request_id: str,
    user_id: str,
):
    """
    **Feature: suitme-image-generation, Property 7: 任务状态转换正确性**
    
    *For any* 任务，不允许逆向转换：completed → processing SHALL 失败。
    """
    async with await get_test_session() as session:
        task_repo = BaseModelTaskRepository(session)
        task_service = TaskService(session)
        
        # 创建任务并完成
        task_id = f"task_{request_id}"
        task = await task_repo.create(
            task_id=task_id,
            request_id=request_id,
            user_id=user_id,
            gender="male",
            height_cm=175.0,
            weight_kg=70.0,
            age=25,
            skin_tone="light",
        )
        await task_repo.update_status(task_id, TaskStatus.PROCESSING)
        await task_repo.update_status(task_id, TaskStatus.COMPLETED)
        
        # 尝试逆向转换（应该失败）
        with pytest.raises(InvalidStatusTransitionError) as exc_info:
            await task_service.update_task_status(task_id, TaskStatus.PROCESSING)
        
        assert exc_info.value.current_status == TaskStatus.COMPLETED
        assert exc_info.value.target_status == TaskStatus.PROCESSING
        
        await session.rollback()


@pytest.mark.asyncio
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    request_id=request_id_strategy,
    user_id=user_id_strategy,
)
async def test_invalid_status_transition_from_failed(
    request_id: str,
    user_id: str,
):
    """
    **Feature: suitme-image-generation, Property 7: 任务状态转换正确性**
    
    *For any* 已失败的任务，不允许任何状态转换。
    """
    async with await get_test_session() as session:
        task_repo = BaseModelTaskRepository(session)
        task_service = TaskService(session)
        
        # 创建任务并标记失败
        task_id = f"task_{request_id}"
        task = await task_repo.create(
            task_id=task_id,
            request_id=request_id,
            user_id=user_id,
            gender="male",
            height_cm=175.0,
            weight_kg=70.0,
            age=25,
            skin_tone="light",
        )
        await task_repo.update_status(task_id, TaskStatus.FAILED, error_message="test error")
        
        # 尝试从 FAILED 转换到其他状态（应该失败）
        with pytest.raises(InvalidStatusTransitionError):
            await task_service.update_task_status(task_id, TaskStatus.PROCESSING)
        
        with pytest.raises(InvalidStatusTransitionError):
            await task_service.complete_task(task_id, image_base64="test")
        
        await session.rollback()
