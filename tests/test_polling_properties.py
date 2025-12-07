"""
属性测试：任务轮询和图片持久化

使用 hypothesis 进行属性测试，验证任务完成后图片持久化的正确性。
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck

from app.database import init_db, create_all_tables, get_session_factory
from app.models import TaskType, TaskStatus
from app.repositories import TaskRepository, ImageRepository
from app.services.polling_service import PollingService


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
angle_strategy = st.sampled_from(["front", "side", "back"])

# 有效的 Base64 图片数据策略（简化版）
# 使用一个最小的有效 1x1 PNG 图片的 Base64
VALID_IMAGE_BASE64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

# 图片 Base64 策略
image_base64_strategy = st.just(VALID_IMAGE_BASE64) | st.none()

# 图片 URL 策略
image_url_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_./"),
    min_size=10,
    max_size=200,
).map(lambda x: f"https://example.com/images/{x}.png") | st.none()


# ============== Property 10: 任务完成图片持久化 ==============
# **Feature: suitme-image-generation, Property 10: 任务完成图片持久化**
# **Validates: Requirements 1.5, 8.2**


@pytest.mark.asyncio
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    request_id=request_id_strategy,
    user_id=user_id_strategy,
    task_type=task_type_strategy,
    angle=angle_strategy,
    image_base64=image_base64_strategy,
    image_url=image_url_strategy,
)
async def test_completed_task_has_image_record(
    request_id: str,
    user_id: str,
    task_type: TaskType,
    angle: str,
    image_base64: str | None,
    image_url: str | None,
):
    """
    **Feature: suitme-image-generation, Property 10: 任务完成图片持久化**
    
    *For any* 完成的任务，ai_generation_image 表中 SHALL 存在对应记录，
    包含 task_id 和图片数据（image_base64 或 image_url 至少一个非空）。
    """
    # 确保至少有一个图片数据
    if image_base64 is None and image_url is None:
        image_base64 = VALID_IMAGE_BASE64
    
    async with await get_test_session() as session:
        task_repo = TaskRepository(session)
        image_repo = ImageRepository(session)
        
        # 创建任务
        task = await task_repo.create(
            request_id=request_id,
            user_id=user_id,
            task_type=task_type,
            angle=angle if task_type == TaskType.OUTFIT else None,
        )
        
        # 先将任务状态更新为 PROCESSING（模拟正常流程）
        await task_repo.update_status(
            task_id=task.id,
            status=TaskStatus.PROCESSING,
            progress=50,
        )
        
        # 创建 PollingService 并模拟任务完成处理
        polling_service = PollingService(session)
        
        # 直接调用内部的完成处理方法
        await polling_service._handle_task_completed(
            task_id=task.id,
            image_base64=image_base64,
            image_url=image_url,
        )
        
        # 验证任务状态已更新为 COMPLETED
        updated_task = await task_repo.get_by_id(task.id)
        assert updated_task is not None
        assert updated_task.status == TaskStatus.COMPLETED
        assert updated_task.progress == 100
        assert updated_task.completed_at is not None
        
        # 验证图片记录已创建
        image = await image_repo.get_by_task_id(task.id)
        assert image is not None
        assert image.task_id == task.id
        
        # 验证至少有一个图片数据非空
        assert image.image_base64 is not None or image.image_url is not None
        
        # 验证图片数据正确
        if image_base64 is not None:
            assert image.image_base64 == image_base64
        if image_url is not None:
            assert image.image_url == image_url
        
        # 验证 angle 正确（outfit 任务）
        if task_type == TaskType.OUTFIT:
            assert image.angle == angle
        
        # 回滚以便下次测试
        await session.rollback()


@pytest.mark.asyncio
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    request_id=request_id_strategy,
    user_id=user_id_strategy,
)
async def test_completed_task_image_with_base64_only(
    request_id: str,
    user_id: str,
):
    """
    **Feature: suitme-image-generation, Property 10: 任务完成图片持久化**
    
    *For any* 完成的任务，当只提供 image_base64 时，
    ai_generation_image 表中 SHALL 存在对应记录且 image_base64 非空。
    """
    async with await get_test_session() as session:
        task_repo = TaskRepository(session)
        image_repo = ImageRepository(session)
        
        # 创建任务
        task = await task_repo.create(
            request_id=request_id,
            user_id=user_id,
            task_type=TaskType.DEFAULT,
        )
        
        # 更新为 PROCESSING
        await task_repo.update_status(
            task_id=task.id,
            status=TaskStatus.PROCESSING,
            progress=50,
        )
        
        # 创建 PollingService 并模拟任务完成处理
        polling_service = PollingService(session)
        
        # 只提供 Base64 数据
        await polling_service._handle_task_completed(
            task_id=task.id,
            image_base64=VALID_IMAGE_BASE64,
            image_url=None,
        )
        
        # 验证图片记录
        image = await image_repo.get_by_task_id(task.id)
        assert image is not None
        assert image.image_base64 == VALID_IMAGE_BASE64
        assert image.image_url is None
        
        await session.rollback()


@pytest.mark.asyncio
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    request_id=request_id_strategy,
    user_id=user_id_strategy,
    image_url=st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_./"),
        min_size=5,
        max_size=100,
    ).map(lambda x: f"https://example.com/{x}.png"),
)
async def test_completed_task_image_with_url_only(
    request_id: str,
    user_id: str,
    image_url: str,
):
    """
    **Feature: suitme-image-generation, Property 10: 任务完成图片持久化**
    
    *For any* 完成的任务，当只提供 image_url 时，
    ai_generation_image 表中 SHALL 存在对应记录且 image_url 非空。
    """
    async with await get_test_session() as session:
        task_repo = TaskRepository(session)
        image_repo = ImageRepository(session)
        
        # 创建任务
        task = await task_repo.create(
            request_id=request_id,
            user_id=user_id,
            task_type=TaskType.DEFAULT,
        )
        
        # 更新为 PROCESSING
        await task_repo.update_status(
            task_id=task.id,
            status=TaskStatus.PROCESSING,
            progress=50,
        )
        
        # 创建 PollingService 并模拟任务完成处理
        polling_service = PollingService(session)
        
        # 只提供 URL
        await polling_service._handle_task_completed(
            task_id=task.id,
            image_base64=None,
            image_url=image_url,
        )
        
        # 验证图片记录
        image = await image_repo.get_by_task_id(task.id)
        assert image is not None
        assert image.image_base64 is None
        assert image.image_url == image_url
        
        await session.rollback()


@pytest.mark.asyncio
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    request_id=request_id_strategy,
    user_id=user_id_strategy,
    image_url=st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_./"),
        min_size=5,
        max_size=100,
    ).map(lambda x: f"https://example.com/{x}.png"),
)
async def test_completed_task_image_with_both(
    request_id: str,
    user_id: str,
    image_url: str,
):
    """
    **Feature: suitme-image-generation, Property 10: 任务完成图片持久化**
    
    *For any* 完成的任务，当同时提供 image_base64 和 image_url 时，
    ai_generation_image 表中 SHALL 存在对应记录且两者都非空。
    """
    async with await get_test_session() as session:
        task_repo = TaskRepository(session)
        image_repo = ImageRepository(session)
        
        # 创建任务
        task = await task_repo.create(
            request_id=request_id,
            user_id=user_id,
            task_type=TaskType.DEFAULT,
        )
        
        # 更新为 PROCESSING
        await task_repo.update_status(
            task_id=task.id,
            status=TaskStatus.PROCESSING,
            progress=50,
        )
        
        # 创建 PollingService 并模拟任务完成处理
        polling_service = PollingService(session)
        
        # 同时提供 Base64 和 URL
        await polling_service._handle_task_completed(
            task_id=task.id,
            image_base64=VALID_IMAGE_BASE64,
            image_url=image_url,
        )
        
        # 验证图片记录
        image = await image_repo.get_by_task_id(task.id)
        assert image is not None
        assert image.image_base64 == VALID_IMAGE_BASE64
        assert image.image_url == image_url
        
        await session.rollback()
