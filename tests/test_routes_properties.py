"""
属性测试：API Routes 层

使用 hypothesis 进行属性测试，验证 API 路由的正确性。
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from app.database import init_db, create_all_tables, drop_all_tables, get_session_factory
from app.models import TaskType, TaskStatus


# ============== 测试应用设置 ==============

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


def create_test_app():
    """创建测试用 FastAPI 应用"""
    from fastapi import FastAPI
    from app.routes import models_router, tasks_router
    
    app = FastAPI()
    app.include_router(models_router)
    app.include_router(tasks_router)
    return app


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


# 有效的 body_profile 策略
body_profile_strategy = st.fixed_dictionaries({
    "gender": st.sampled_from(["male", "female"]),
    "height_cm": st.floats(min_value=50, max_value=250, allow_nan=False, allow_infinity=False),
    "weight_kg": st.floats(min_value=20, max_value=300, allow_nan=False, allow_infinity=False),
    "age": st.integers(min_value=1, max_value=120),
    "skin_tone": st.text(min_size=1, max_size=20),
})

# 有效的 Data URI 策略
VALID_DATA_URI = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

# 角度策略
angle_strategy = st.sampled_from(["front", "side", "back"])

# 不存在的 task_id 策略
nonexistent_task_id_strategy = st.integers(min_value=100000, max_value=999999)


# ============== Property 1: 任务创建返回正确响应 ==============
# **Feature: suitme-image-generation, Property 1: 任务创建返回正确响应**
# **Validates: Requirements 1.1, 2.1, 3.1**


@pytest.mark.asyncio
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    request_id=request_id_strategy,
    user_id=user_id_strategy,
    body_profile=body_profile_strategy,
)
async def test_default_model_creation_returns_correct_response(
    request_id: str,
    user_id: str,
    body_profile: dict,
):
    """
    **Feature: suitme-image-generation, Property 1: 任务创建返回正确响应**
    
    *For any* 有效的默认模特生成请求，提交后服务 SHALL 返回包含有效 task_id 
    和 status="submitted" 的响应，HTTP 状态码为 202。
    
    **Validates: Requirements 1.1**
    """
    await ensure_db_initialized()
    
    app = create_test_app()
    
    # Mock Apimart client to avoid external calls
    with patch("app.services.model_service.ApimartClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.submit_generation.return_value = "external-task-123"
        MockClient.return_value = mock_instance
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/models/default",
                json={
                    "request_id": request_id,
                    "user_id": user_id,
                    "user_image_base64": VALID_DATA_URI,
                    "body_profile": body_profile,
                },
            )
            
            # 验证 HTTP 状态码为 202
            assert response.status_code == 202, f"Expected 202, got {response.status_code}"
            
            # 验证响应结构
            data = response.json()
            assert data["code"] == 0
            assert data["msg"] == "accepted"
            assert "data" in data
            assert "task_id" in data["data"]
            assert data["data"]["status"] == "submitted"
            assert isinstance(data["data"]["task_id"], int)
            assert data["data"]["task_id"] > 0


@pytest.mark.asyncio
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    request_id=request_id_strategy,
    user_id=user_id_strategy,
    edit_instructions=st.text(min_size=1, max_size=100),
)
async def test_edit_model_creation_returns_correct_response(
    request_id: str,
    user_id: str,
    edit_instructions: str,
):
    """
    **Feature: suitme-image-generation, Property 1: 任务创建返回正确响应**
    
    *For any* 有效的模特编辑请求（存在的 base_model_task_id），提交后服务 SHALL 
    返回包含有效 task_id 和 status="submitted" 的响应，HTTP 状态码为 202。
    
    **Validates: Requirements 2.1**
    """
    await ensure_db_initialized()
    
    app = create_test_app()
    
    # 首先创建一个基础模特任务
    async with await get_test_session() as session:
        from app.repositories import BaseModelTaskRepository
        task_repo = BaseModelTaskRepository(session)
        base_task = await task_repo.create(
            task_id=f"base-{request_id}",
            request_id="base-" + request_id,
            user_id=user_id,
            gender="male",
            height_cm=175.0,
            weight_kg=70.0,
            age=25,
            skin_tone="light",
        )
        await session.commit()
        base_task_id = base_task.task_id
    
    # Mock Apimart client
    with patch("app.services.model_service.ApimartClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.submit_generation.return_value = "external-task-456"
        MockClient.return_value = mock_instance
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/models/edit",
                json={
                    "request_id": request_id,
                    "user_id": user_id,
                    "base_model_task_id": base_task_id,
                    "edit_instructions": edit_instructions,
                },
            )
            
            # 验证 HTTP 状态码为 202
            assert response.status_code == 202, f"Expected 202, got {response.status_code}"
            
            # 验证响应结构
            data = response.json()
            assert data["code"] == 0
            assert data["msg"] == "accepted"
            assert "data" in data
            assert "task_id" in data["data"]
            assert data["data"]["status"] == "submitted"


@pytest.mark.asyncio
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    request_id=request_id_strategy,
    user_id=user_id_strategy,
    angle=angle_strategy,
)
async def test_outfit_creation_returns_correct_response(
    request_id: str,
    user_id: str,
    angle: str,
):
    """
    **Feature: suitme-image-generation, Property 1: 任务创建返回正确响应**
    
    *For any* 有效的穿搭生成请求（存在的 base_model_task_id），提交后服务 SHALL 
    返回包含有效 task_id、status="submitted" 和 angle 的响应，HTTP 状态码为 202。
    
    **Validates: Requirements 3.1**
    """
    await ensure_db_initialized()
    
    app = create_test_app()
    
    # 首先创建一个基础模特任务
    async with await get_test_session() as session:
        from app.repositories import BaseModelTaskRepository
        task_repo = BaseModelTaskRepository(session)
        base_task = await task_repo.create(
            task_id=f"base-outfit-{request_id}",
            request_id="base-outfit-" + request_id,
            user_id=user_id,
            gender="male",
            height_cm=175.0,
            weight_kg=70.0,
            age=25,
            skin_tone="light",
        )
        await session.commit()
        base_task_id = base_task.task_id
    
    # Mock Apimart client
    with patch("app.services.model_service.ApimartClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.submit_generation.return_value = "external-task-789"
        MockClient.return_value = mock_instance
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/models/outfit",
                json={
                    "request_id": request_id,
                    "user_id": user_id,
                    "base_model_task_id": base_task_id,
                    "angle": angle,
                    "outfit_image_urls": ["https://example.com/outfit1.jpg"],
                },
            )
            
            # 验证 HTTP 状态码为 202
            assert response.status_code == 202, f"Expected 202, got {response.status_code}"
            
            # 验证响应结构
            data = response.json()
            assert data["code"] == 0
            assert data["msg"] == "accepted"
            assert "data" in data
            assert "task_id" in data["data"]
            assert data["data"]["status"] == "submitted"
            assert data["data"]["angle"] == angle



# ============== Property 8: 任务查询返回正确信息 ==============
# **Feature: suitme-image-generation, Property 8: 任务查询返回正确信息**
# **Validates: Requirements 5.1, 5.3**


@pytest.mark.asyncio
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    request_id=request_id_strategy,
    user_id=user_id_strategy,
)
async def test_task_query_returns_correct_info_for_submitted_task(
    request_id: str,
    user_id: str,
):
    """
    **Feature: suitme-image-generation, Property 8: 任务查询返回正确信息**
    
    *For any* 存在的 task_id，查询 SHALL 返回当前状态和进度。
    
    **Validates: Requirements 5.1**
    """
    await ensure_db_initialized()
    
    app = create_test_app()
    
    # 创建一个任务
    async with await get_test_session() as session:
        from app.repositories import BaseModelTaskRepository
        task_repo = BaseModelTaskRepository(session)
        task = await task_repo.create(
            task_id=f"query-{request_id}",
            request_id=request_id,
            user_id=user_id,
            gender="male",
            height_cm=175.0,
            weight_kg=70.0,
            age=25,
            skin_tone="light",
        )
        await session.commit()
        task_id = task.task_id
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get(f"/tasks/{task_id}")
        
        # 验证 HTTP 状态码为 200
        assert response.status_code == 200
        
        # 验证响应结构
        data = response.json()
        assert data["code"] == 0
        assert data["msg"] == "success"
        assert "data" in data
        assert data["data"]["task_id"] == task_id
        assert data["data"]["status"] == "submitted"
        assert "progress" in data["data"]
        assert data["data"]["type"] == "model"


@pytest.mark.asyncio
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    request_id=request_id_strategy,
    user_id=user_id_strategy,
)
async def test_task_query_returns_image_for_completed_task(
    request_id: str,
    user_id: str,
):
    """
    **Feature: suitme-image-generation, Property 8: 任务查询返回正确信息**
    
    *For any* 状态为 completed 的任务，响应 SHALL 包含图片信息（Base64 或 URL）。
    
    **Validates: Requirements 5.3**
    """
    await ensure_db_initialized()
    
    app = create_test_app()
    
    # 创建一个已完成的任务
    async with await get_test_session() as session:
        from app.repositories import BaseModelTaskRepository, ImageRepository
        
        task_repo = BaseModelTaskRepository(session)
        image_repo = ImageRepository(session)
        
        # 创建任务
        task = await task_repo.create(
            task_id=f"completed-{request_id}",
            request_id=request_id,
            user_id=user_id,
            gender="male",
            height_cm=175.0,
            weight_kg=70.0,
            age=25,
            skin_tone="light",
        )
        
        # 更新状态为 COMPLETED
        await task_repo.update_status(task.task_id, TaskStatus.PROCESSING)
        await task_repo.update_status(task.task_id, TaskStatus.COMPLETED, progress=100)
        
        # 创建图片记录
        await image_repo.create(
            task_type=TaskType.MODEL,
            task_id=task.id,
            image_base64="test_image_base64_data",
        )
        
        await session.commit()
        task_id = task.task_id
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get(f"/tasks/{task_id}")
        
        # 验证 HTTP 状态码为 200
        assert response.status_code == 200
        
        # 验证响应结构
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["status"] == "completed"
        assert data["data"]["progress"] == 100
        
        # 验证包含图片信息
        assert "image" in data["data"]
        assert data["data"]["image"] is not None
        image_data = data["data"]["image"]
        # 至少有一个图片字段非空
        assert image_data.get("image_base64") is not None or image_data.get("image_url") is not None


# ============== Property 9: 不存在任务查询返回 404 ==============
# **Feature: suitme-image-generation, Property 9: 不存在任务查询返回 404**
# **Validates: Requirements 5.2**


@pytest.mark.asyncio
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    nonexistent_task_id=nonexistent_task_id_strategy,
)
async def test_nonexistent_task_query_returns_404(
    nonexistent_task_id: int,
):
    """
    **Feature: suitme-image-generation, Property 9: 不存在任务查询返回 404**
    
    *For any* 不存在于数据库中的 task_id，查询 SHALL 返回 HTTP 404 和 code=1003。
    
    **Validates: Requirements 5.2**
    """
    await ensure_db_initialized()
    
    app = create_test_app()
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get(f"/tasks/{nonexistent_task_id}")
        
        # 验证 HTTP 状态码为 404
        assert response.status_code == 404
        
        # 验证错误响应结构
        data = response.json()
        assert "detail" in data
        assert data["detail"]["code"] == 1003
