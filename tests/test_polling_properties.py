"""
属性测试：任务轮询和图片持久化

使用 hypothesis 进行属性测试，验证任务完成后图片持久化的正确性。
更新为使用新的分离任务表结构。
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck

from app.database import init_db, create_all_tables, get_session_factory
from app.models import TaskType, TaskStatus
from app.repositories import (
    BaseModelTaskRepository,
    EditTaskRepository,
    OutfitTaskRepository,
    ImageRepository,
)
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
# **Feature: database-refactor, Property 10: 任务完成图片持久化**
# **Validates: Requirements 2.4**


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
    image_base64=image_base64_strategy,
    image_url=image_url_strategy,
)
async def test_completed_task_has_image_record(
    task_id: str,
    request_id: str,
    user_id: str,
    gender: str,
    height_cm: float,
    weight_kg: float,
    age: int,
    skin_tone: str,
    image_base64: str | None,
    image_url: str | None,
):
    """
    **Feature: database-refactor, Property 10: 任务完成图片持久化**
    
    *For any* 完成的任务，generation_image 表中 SHALL 存在对应记录，
    包含 task_type、task_id 和图片数据（image_base64 或 image_url 至少一个非空）。
    """
    # 确保至少有一个图片数据
    if image_base64 is None and image_url is None:
        image_base64 = VALID_IMAGE_BASE64
    
    async with await get_test_session() as session:
        base_repo = BaseModelTaskRepository(session)
        image_repo = ImageRepository(session)
        
        # 创建 BaseModelTask
        task = await base_repo.create(
            task_id=task_id,
            request_id=request_id,
            user_id=user_id,
            gender=gender,
            height_cm=height_cm,
            weight_kg=weight_kg,
            age=age,
            skin_tone=skin_tone,
        )
        
        # 先将任务状态更新为 PROCESSING（模拟正常流程）
        await base_repo.update_status(
            task_id=task_id,
            status=TaskStatus.PROCESSING,
            progress=50,
        )
        
        # 创建 PollingService 并模拟任务完成处理
        polling_service = PollingService(session)
        
        # 直接调用内部的完成处理方法
        await polling_service._handle_task_completed(
            task_id=task_id,
            image_base64=image_base64,
            image_url=image_url,
        )
        
        # 验证任务状态已更新为 COMPLETED
        updated_task = await base_repo.get_by_task_id(task_id)
        assert updated_task is not None
        assert updated_task.status == TaskStatus.COMPLETED
        assert updated_task.progress == 100
        assert updated_task.completed_at is not None
        
        # 验证图片记录已创建
        image = await image_repo.get_by_task(TaskType.MODEL, task.id)
        assert image is not None
        assert image.task_id == task.id
        assert image.task_type == TaskType.MODEL
        
        # 验证至少有一个图片数据非空
        assert image.image_base64 is not None or image.image_url is not None
        
        # 验证图片数据正确
        if image_base64 is not None:
            assert image.image_base64 == image_base64
        if image_url is not None:
            assert image.image_url == image_url
        
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
async def test_completed_task_image_with_base64_only(
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
    **Feature: database-refactor, Property 10: 任务完成图片持久化**
    
    *For any* 完成的任务，当只提供 image_base64 时，
    generation_image 表中 SHALL 存在对应记录且 image_base64 非空。
    """
    async with await get_test_session() as session:
        base_repo = BaseModelTaskRepository(session)
        image_repo = ImageRepository(session)
        
        # 创建任务
        task = await base_repo.create(
            task_id=task_id,
            request_id=request_id,
            user_id=user_id,
            gender=gender,
            height_cm=height_cm,
            weight_kg=weight_kg,
            age=age,
            skin_tone=skin_tone,
        )
        
        # 更新为 PROCESSING
        await base_repo.update_status(
            task_id=task_id,
            status=TaskStatus.PROCESSING,
            progress=50,
        )
        
        # 创建 PollingService 并模拟任务完成处理
        polling_service = PollingService(session)
        
        # 只提供 Base64 数据
        await polling_service._handle_task_completed(
            task_id=task_id,
            image_base64=VALID_IMAGE_BASE64,
            image_url=None,
        )
        
        # 验证图片记录
        image = await image_repo.get_by_task(TaskType.MODEL, task.id)
        assert image is not None
        assert image.image_base64 == VALID_IMAGE_BASE64
        assert image.image_url is None
        
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
    image_url=st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_./"),
        min_size=5,
        max_size=100,
    ).map(lambda x: f"https://example.com/{x}.png"),
)
async def test_completed_task_image_with_url_only(
    task_id: str,
    request_id: str,
    user_id: str,
    gender: str,
    height_cm: float,
    weight_kg: float,
    age: int,
    skin_tone: str,
    image_url: str,
):
    """
    **Feature: database-refactor, Property 10: 任务完成图片持久化**
    
    *For any* 完成的任务，当只提供 image_url 时，
    generation_image 表中 SHALL 存在对应记录且 image_url 非空。
    """
    async with await get_test_session() as session:
        base_repo = BaseModelTaskRepository(session)
        image_repo = ImageRepository(session)
        
        # 创建任务
        task = await base_repo.create(
            task_id=task_id,
            request_id=request_id,
            user_id=user_id,
            gender=gender,
            height_cm=height_cm,
            weight_kg=weight_kg,
            age=age,
            skin_tone=skin_tone,
        )
        
        # 更新为 PROCESSING
        await base_repo.update_status(
            task_id=task_id,
            status=TaskStatus.PROCESSING,
            progress=50,
        )
        
        # 创建 PollingService 并模拟任务完成处理
        polling_service = PollingService(session)
        
        # 只提供 URL
        await polling_service._handle_task_completed(
            task_id=task_id,
            image_base64=None,
            image_url=image_url,
        )
        
        # 验证图片记录
        image = await image_repo.get_by_task(TaskType.MODEL, task.id)
        assert image is not None
        assert image.image_base64 is None
        assert image.image_url == image_url
        
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
    image_url=st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_./"),
        min_size=5,
        max_size=100,
    ).map(lambda x: f"https://example.com/{x}.png"),
)
async def test_completed_task_image_with_both(
    task_id: str,
    request_id: str,
    user_id: str,
    gender: str,
    height_cm: float,
    weight_kg: float,
    age: int,
    skin_tone: str,
    image_url: str,
):
    """
    **Feature: database-refactor, Property 10: 任务完成图片持久化**
    
    *For any* 完成的任务，当同时提供 image_base64 和 image_url 时，
    generation_image 表中 SHALL 存在对应记录且两者都非空。
    """
    async with await get_test_session() as session:
        base_repo = BaseModelTaskRepository(session)
        image_repo = ImageRepository(session)
        
        # 创建任务
        task = await base_repo.create(
            task_id=task_id,
            request_id=request_id,
            user_id=user_id,
            gender=gender,
            height_cm=height_cm,
            weight_kg=weight_kg,
            age=age,
            skin_tone=skin_tone,
        )
        
        # 更新为 PROCESSING
        await base_repo.update_status(
            task_id=task_id,
            status=TaskStatus.PROCESSING,
            progress=50,
        )
        
        # 创建 PollingService 并模拟任务完成处理
        polling_service = PollingService(session)
        
        # 同时提供 Base64 和 URL
        await polling_service._handle_task_completed(
            task_id=task_id,
            image_base64=VALID_IMAGE_BASE64,
            image_url=image_url,
        )
        
        # 验证图片记录
        image = await image_repo.get_by_task(TaskType.MODEL, task.id)
        assert image is not None
        assert image.image_base64 == VALID_IMAGE_BASE64
        assert image.image_url == image_url
        
        await session.rollback()


# ============== Property: Outfit 任务图片关联 ==============
# **Feature: database-refactor, Property: Outfit 任务图片关联**
# **Validates: Requirements 2.4**


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
)
async def test_outfit_task_image_has_angle(
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
):
    """
    **Feature: database-refactor, Property: Outfit 任务图片关联**
    
    *For any* 完成的 OutfitTask，generation_image 表中 SHALL 存在对应记录，
    且 angle 字段正确设置。
    """
    async with await get_test_session() as session:
        base_repo = BaseModelTaskRepository(session)
        outfit_repo = OutfitTaskRepository(session)
        image_repo = ImageRepository(session)
        
        # 创建 BaseModelTask
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
        )
        
        # 更新为 PROCESSING
        await outfit_repo.update_status(
            task_id=outfit_task_id,
            status=TaskStatus.PROCESSING,
            progress=50,
        )
        
        # 创建 PollingService 并模拟任务完成处理
        polling_service = PollingService(session)
        
        await polling_service._handle_task_completed(
            task_id=outfit_task_id,
            image_base64=VALID_IMAGE_BASE64,
            image_url=None,
        )
        
        # 验证图片记录
        image = await image_repo.get_by_task(TaskType.OUTFIT, outfit_task.id)
        assert image is not None
        assert image.task_type == TaskType.OUTFIT
        assert image.task_id == outfit_task.id
        assert image.angle == angle
        assert image.image_base64 == VALID_IMAGE_BASE64
        
        await session.rollback()
