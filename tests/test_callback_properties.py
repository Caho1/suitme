"""
属性测试：回调处理

使用 hypothesis 进行属性测试，验证回调包含正确信息。
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import AsyncMock, patch
import httpx

from app.infra.callback_handler import CallbackHandler, CallbackPayload


# ============== 测试策略 ==============

# 任务 ID 策略
task_id_strategy = st.integers(min_value=1, max_value=1000000)

# 任务状态策略（回调只发送 completed 或 failed）
status_strategy = st.sampled_from(["completed", "failed"])

# 任务类型策略
task_type_strategy = st.sampled_from(["default", "edit", "outfit"])

# 角度策略
angle_strategy = st.sampled_from(["front", "side", "back"]) | st.none()

# 有效的 Base64 图片数据策略
VALID_IMAGE_BASE64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
image_base64_strategy = st.just(VALID_IMAGE_BASE64) | st.none()

# 图片 URL 策略
image_url_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_./"),
    min_size=10,
    max_size=100,
).map(lambda x: f"https://example.com/images/{x}.png") | st.none()

# 错误信息策略
error_message_strategy = st.text(min_size=1, max_size=200) | st.none()


# ============== Property 11: 回调包含正确信息 ==============
# **Feature: suitme-image-generation, Property 11: 回调包含正确信息**
# **Validates: Requirements 7.1, 7.3**


@pytest.mark.asyncio
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    task_id=task_id_strategy,
    status=status_strategy,
    task_type=task_type_strategy,
    angle=angle_strategy,
    image_base64=image_base64_strategy,
    image_url=image_url_strategy,
    error_message=error_message_strategy,
)
async def test_callback_contains_required_fields(
    task_id: int,
    status: str,
    task_type: str,
    angle: str | None,
    image_base64: str | None,
    image_url: str | None,
    error_message: str | None,
):
    """
    **Feature: suitme-image-generation, Property 11: 回调包含正确信息**
    
    *For any* 完成或失败的任务，回调请求 SHALL 包含 task_id、status、type，
    且请求头包含身份验证 token。
    
    **Validates: Requirements 7.1, 7.3**
    """
    # 记录实际发送的请求
    captured_request = {}
    
    async def mock_post(url, json, headers):
        captured_request["url"] = url
        captured_request["json"] = json
        captured_request["headers"] = headers
        # 返回成功响应
        response = AsyncMock()
        response.status_code = 200
        response.text = "OK"
        return response
    
    # 创建 mock HTTP 客户端
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = mock_post
    
    # 配置回调 URL 和 token
    with patch("app.infra.callback_handler.get_settings") as mock_settings:
        settings_instance = AsyncMock()
        settings_instance.callback_url = "https://java-backend.example.com/callback"
        settings_instance.callback_token = "test-auth-token-12345"
        settings_instance.callback_max_retries = 3
        settings_instance.retry_base_delay = 0.01  # 快速重试用于测试
        settings_instance.http_timeout = 30.0
        mock_settings.return_value = settings_instance
        
        handler = CallbackHandler(http_client=mock_client)
        
        result = await handler.notify_java(
            task_id=task_id,
            status=status,
            task_type=task_type,
            angle=angle,
            image_base64=image_base64,
            image_url=image_url,
            error_message=error_message,
        )
        
        # 验证回调成功
        assert result is True
        
        # 验证请求体包含必需字段
        json_body = captured_request["json"]
        assert "task_id" in json_body
        assert json_body["task_id"] == task_id
        assert "status" in json_body
        assert json_body["status"] == status
        assert "type" in json_body
        assert json_body["type"] == task_type
        
        # 验证请求头包含身份验证 token
        headers = captured_request["headers"]
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-auth-token-12345"
        assert headers["Content-Type"] == "application/json"
        
        # 验证可选字段正确传递
        if angle is not None:
            assert json_body.get("angle") == angle
        else:
            assert "angle" not in json_body
            
        if image_base64 is not None:
            assert json_body.get("image_base64") == image_base64
        else:
            assert "image_base64" not in json_body
            
        if image_url is not None:
            assert json_body.get("image_url") == image_url
        else:
            assert "image_url" not in json_body
            
        if error_message is not None:
            assert json_body.get("error_message") == error_message
        else:
            assert "error_message" not in json_body


@pytest.mark.asyncio
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    task_id=task_id_strategy,
    task_type=task_type_strategy,
)
async def test_callback_completed_task_contains_task_info(
    task_id: int,
    task_type: str,
):
    """
    **Feature: suitme-image-generation, Property 11: 回调包含正确信息**
    
    *For any* 完成的任务，回调请求 SHALL 包含 task_id、status="completed"、type。
    
    **Validates: Requirements 7.1**
    """
    captured_request = {}
    
    async def mock_post(url, json, headers):
        captured_request["json"] = json
        captured_request["headers"] = headers
        response = AsyncMock()
        response.status_code = 200
        return response
    
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = mock_post
    
    with patch("app.infra.callback_handler.get_settings") as mock_settings:
        settings_instance = AsyncMock()
        settings_instance.callback_url = "https://java-backend.example.com/callback"
        settings_instance.callback_token = "auth-token"
        settings_instance.callback_max_retries = 3
        settings_instance.retry_base_delay = 0.01
        settings_instance.http_timeout = 30.0
        mock_settings.return_value = settings_instance
        
        handler = CallbackHandler(http_client=mock_client)
        
        await handler.notify_java(
            task_id=task_id,
            status="completed",
            task_type=task_type,
            image_base64=VALID_IMAGE_BASE64,
        )
        
        json_body = captured_request["json"]
        
        # 验证必需字段
        assert json_body["task_id"] == task_id
        assert json_body["status"] == "completed"
        assert json_body["type"] == task_type


@pytest.mark.asyncio
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    task_id=task_id_strategy,
    task_type=task_type_strategy,
    error_message=st.text(min_size=1, max_size=100),
)
async def test_callback_failed_task_contains_error_info(
    task_id: int,
    task_type: str,
    error_message: str,
):
    """
    **Feature: suitme-image-generation, Property 11: 回调包含正确信息**
    
    *For any* 失败的任务，回调请求 SHALL 包含 task_id、status="failed"、type 和 error_message。
    
    **Validates: Requirements 7.1**
    """
    captured_request = {}
    
    async def mock_post(url, json, headers):
        captured_request["json"] = json
        response = AsyncMock()
        response.status_code = 200
        return response
    
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = mock_post
    
    with patch("app.infra.callback_handler.get_settings") as mock_settings:
        settings_instance = AsyncMock()
        settings_instance.callback_url = "https://java-backend.example.com/callback"
        settings_instance.callback_token = "auth-token"
        settings_instance.callback_max_retries = 3
        settings_instance.retry_base_delay = 0.01
        settings_instance.http_timeout = 30.0
        mock_settings.return_value = settings_instance
        
        handler = CallbackHandler(http_client=mock_client)
        
        await handler.notify_java(
            task_id=task_id,
            status="failed",
            task_type=task_type,
            error_message=error_message,
        )
        
        json_body = captured_request["json"]
        
        # 验证必需字段
        assert json_body["task_id"] == task_id
        assert json_body["status"] == "failed"
        assert json_body["type"] == task_type
        assert json_body["error_message"] == error_message


@pytest.mark.asyncio
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    task_id=task_id_strategy,
    auth_token=st.text(min_size=10, max_size=100),
)
async def test_callback_includes_auth_token_in_header(
    task_id: int,
    auth_token: str,
):
    """
    **Feature: suitme-image-generation, Property 11: 回调包含正确信息**
    
    *For any* 回调请求，请求头 SHALL 包含身份验证 token。
    
    **Validates: Requirements 7.3**
    """
    captured_request = {}
    
    async def mock_post(url, json, headers):
        captured_request["headers"] = headers
        response = AsyncMock()
        response.status_code = 200
        return response
    
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = mock_post
    
    with patch("app.infra.callback_handler.get_settings") as mock_settings:
        settings_instance = AsyncMock()
        settings_instance.callback_url = "https://java-backend.example.com/callback"
        settings_instance.callback_token = auth_token
        settings_instance.callback_max_retries = 3
        settings_instance.retry_base_delay = 0.01
        settings_instance.http_timeout = 30.0
        mock_settings.return_value = settings_instance
        
        handler = CallbackHandler(http_client=mock_client)
        
        await handler.notify_java(
            task_id=task_id,
            status="completed",
            task_type="default",
        )
        
        headers = captured_request["headers"]
        
        # 验证 Authorization 头
        assert "Authorization" in headers
        assert headers["Authorization"] == f"Bearer {auth_token}"


# ============== CallbackPayload 单元测试 ==============


@pytest.mark.asyncio
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    task_id=task_id_strategy,
    status=status_strategy,
    task_type=task_type_strategy,
    angle=angle_strategy,
    image_base64=image_base64_strategy,
    image_url=image_url_strategy,
    error_message=error_message_strategy,
)
async def test_callback_payload_to_dict_excludes_none(
    task_id: int,
    status: str,
    task_type: str,
    angle: str | None,
    image_base64: str | None,
    image_url: str | None,
    error_message: str | None,
):
    """
    **Feature: suitme-image-generation, Property 11: 回调包含正确信息**
    
    *For any* CallbackPayload，to_dict() 方法 SHALL 排除 None 值字段，
    只包含非空字段。
    
    **Validates: Requirements 7.1**
    """
    payload = CallbackPayload(
        task_id=task_id,
        status=status,
        type=task_type,
        angle=angle,
        image_base64=image_base64,
        image_url=image_url,
        error_message=error_message,
    )
    
    result = payload.to_dict()
    
    # 必需字段始终存在
    assert result["task_id"] == task_id
    assert result["status"] == status
    assert result["type"] == task_type
    
    # 可选字段：非 None 时存在，None 时不存在
    if angle is not None:
        assert result["angle"] == angle
    else:
        assert "angle" not in result
        
    if image_base64 is not None:
        assert result["image_base64"] == image_base64
    else:
        assert "image_base64" not in result
        
    if image_url is not None:
        assert result["image_url"] == image_url
    else:
        assert "image_url" not in result
        
    if error_message is not None:
        assert result["error_message"] == error_message
    else:
        assert "error_message" not in result
