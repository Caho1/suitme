"""
属性测试：Pydantic Schema 验证

使用 hypothesis 进行属性测试，验证数据验证逻辑的正确性。
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from pydantic import ValidationError

from app.schemas import (
    DefaultModelRequest,
    OutfitModelRequest,
    BodyProfile,
    is_valid_data_uri,
    AngleType,
)


# ============== 测试辅助函数 ==============

def generate_valid_data_uri(image_data: bytes = b"test") -> str:
    """生成有效的 Data URI"""
    import base64
    encoded = base64.b64encode(image_data).decode()
    return f"data:image/png;base64,{encoded}"


# ============== Property 2: 无效 Base64 输入拒绝 ==============
# **Feature: suitme-image-generation, Property 2: 无效 Base64 输入拒绝**
# **Validates: Requirements 1.2**


# 生成无效 Data URI 的策略
invalid_data_uri_strategy = st.one_of(
    # 空字符串
    st.just(""),
    # 纯文本（非 Data URI 格式）
    st.text(min_size=1, max_size=100).filter(
        lambda x: not x.startswith("data:")
    ),
    # 缺少 base64 标记
    st.text(min_size=1, max_size=50).map(
        lambda x: f"data:image/png,{x}"
    ),
    # 错误的 MIME 类型
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=10).map(
        lambda x: f"data:{x};base64,dGVzdA=="
    ),
    # 无效的 base64 字符
    st.text(alphabet="!@#$%^&*()", min_size=1, max_size=20).map(
        lambda x: f"data:image/png;base64,{x}"
    ),
    # 格式正确但 base64 内容无效（包含非法字符）
    st.text(min_size=5, max_size=50).filter(
        lambda x: any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=" for c in x)
    ).map(
        lambda x: f"data:image/png;base64,{x}"
    ),
)


@settings(max_examples=100)
@given(invalid_base64=invalid_data_uri_strategy)
def test_invalid_base64_rejected_default_model(invalid_base64: str):
    """
    **Feature: suitme-image-generation, Property 2: 无效 Base64 输入拒绝**
    
    *For any* 不符合 Data URI 格式的 user_image_base64 字符串，
    DefaultModelRequest 验证 SHALL 抛出 ValidationError。
    """
    # 确保生成的值确实是无效的
    assume(not is_valid_data_uri(invalid_base64))
    
    with pytest.raises(ValidationError) as exc_info:
        DefaultModelRequest(
            request_id="test-request-001",
            user_id="user-001",
            user_image_base64=invalid_base64,
            body_profile={
                "gender": "male",
                "height_cm": 175.0,
                "weight_kg": 70.0,
                "age": 25,
                "skin_tone": "light",
            }
        )
    
    # 验证错误与 user_image_base64 字段相关
    errors = exc_info.value.errors()
    field_errors = [e for e in errors if "user_image_base64" in str(e.get("loc", []))]
    assert len(field_errors) > 0, f"Expected error on user_image_base64, got: {errors}"


@settings(max_examples=100)
@given(empty_url=st.sampled_from(["", "   ", "\t", "\n"]))
def test_empty_outfit_url_rejected(empty_url: str):
    """
    **Feature: suitme-image-generation, Property 2: 空图片路径拒绝**
    
    *For any* 空字符串或纯空白字符的 outfit_image_urls，
    OutfitModelRequest 验证 SHALL 抛出 ValidationError。
    """
    with pytest.raises(ValidationError) as exc_info:
        OutfitModelRequest(
            request_id="test-request-001",
            user_id="user-001",
            base_model_task_id=1,
            angle="front",
            outfit_image_urls=[empty_url],
        )
    
    errors = exc_info.value.errors()
    field_errors = [e for e in errors if "outfit_image_urls" in str(e.get("loc", []))]
    assert len(field_errors) > 0, f"Expected error on outfit_image_urls, got: {errors}"



# ============== Property 3: 无效 body_profile 参数拒绝 ==============
# **Feature: suitme-image-generation, Property 3: 无效 body_profile 参数拒绝**
# **Validates: Requirements 1.3**


# 生成无效 body_profile 的策略（超出合理范围）
invalid_body_profile_strategy = st.one_of(
    # 负数身高
    st.builds(
        dict,
        gender=st.just("male"),
        height_cm=st.floats(max_value=0, allow_nan=False, allow_infinity=False),
        weight_kg=st.just(70.0),
        age=st.just(25),
        skin_tone=st.just("light"),
    ),
    # 负数体重
    st.builds(
        dict,
        gender=st.just("male"),
        height_cm=st.just(175.0),
        weight_kg=st.floats(max_value=0, allow_nan=False, allow_infinity=False),
        age=st.just(25),
        skin_tone=st.just("light"),
    ),
    # 负数或零年龄
    st.builds(
        dict,
        gender=st.just("male"),
        height_cm=st.just(175.0),
        weight_kg=st.just(70.0),
        age=st.integers(max_value=0),
        skin_tone=st.just("light"),
    ),
    # 超出上限的身高 (>300cm)
    st.builds(
        dict,
        gender=st.just("male"),
        height_cm=st.floats(min_value=301, max_value=1000, allow_nan=False, allow_infinity=False),
        weight_kg=st.just(70.0),
        age=st.just(25),
        skin_tone=st.just("light"),
    ),
    # 超出上限的体重 (>500kg)
    st.builds(
        dict,
        gender=st.just("male"),
        height_cm=st.just(175.0),
        weight_kg=st.floats(min_value=501, max_value=1000, allow_nan=False, allow_infinity=False),
        age=st.just(25),
        skin_tone=st.just("light"),
    ),
    # 超出上限的年龄 (>150)
    st.builds(
        dict,
        gender=st.just("male"),
        height_cm=st.just(175.0),
        weight_kg=st.just(70.0),
        age=st.integers(min_value=151, max_value=500),
        skin_tone=st.just("light"),
    ),
)


@settings(max_examples=100)
@given(invalid_profile=invalid_body_profile_strategy)
def test_invalid_body_profile_rejected(invalid_profile: dict):
    """
    **Feature: suitme-image-generation, Property 3: 无效 body_profile 参数拒绝**
    
    *For any* body_profile 中包含超出合理范围值的请求
    （如负数身高、负数体重、负数年龄、超出上限的值），
    BodyProfile 验证 SHALL 抛出 ValidationError。
    """
    with pytest.raises(ValidationError):
        BodyProfile(**invalid_profile)


@settings(max_examples=100)
@given(invalid_profile=invalid_body_profile_strategy)
def test_invalid_body_profile_rejected_in_request(invalid_profile: dict):
    """
    **Feature: suitme-image-generation, Property 3: 无效 body_profile 参数拒绝**
    
    *For any* body_profile 中包含超出合理范围值的 DefaultModelRequest，
    验证 SHALL 抛出 ValidationError。
    """
    valid_image = generate_valid_data_uri()
    
    with pytest.raises(ValidationError) as exc_info:
        DefaultModelRequest(
            request_id="test-request-001",
            user_id="user-001",
            user_image_base64=valid_image,
            body_profile=invalid_profile,
        )
    
    # 验证错误与 body_profile 字段相关
    errors = exc_info.value.errors()
    body_profile_errors = [
        e for e in errors 
        if "body_profile" in str(e.get("loc", []))
    ]
    assert len(body_profile_errors) > 0, f"Expected error on body_profile, got: {errors}"



# ============== Property 5: 无效 angle 参数拒绝 ==============
# **Feature: suitme-image-generation, Property 5: 无效 angle 参数拒绝**
# **Validates: Requirements 3.2**


# 有效的 angle 值
VALID_ANGLES = {"front", "side", "back"}

# 生成无效 angle 的策略
invalid_angle_strategy = st.text(min_size=1, max_size=20).filter(
    lambda x: x.lower() not in VALID_ANGLES
)


@settings(max_examples=100)
@given(invalid_angle=invalid_angle_strategy)
def test_invalid_angle_rejected(invalid_angle: str):
    """
    **Feature: suitme-image-generation, Property 5: 无效 angle 参数拒绝**
    
    *For any* 不在 ["front", "side", "back"] 枚举中的 angle 值，
    OutfitModelRequest 验证 SHALL 抛出 ValidationError。
    """
    valid_urls = ["https://example.com/outfit.jpg"]
    
    with pytest.raises(ValidationError) as exc_info:
        OutfitModelRequest(
            request_id="test-request-001",
            user_id="user-001",
            base_model_task_id=1,
            angle=invalid_angle,
            outfit_image_urls=valid_urls,
        )
    
    # 验证错误与 angle 字段相关
    errors = exc_info.value.errors()
    angle_errors = [e for e in errors if "angle" in str(e.get("loc", []))]
    assert len(angle_errors) > 0, f"Expected error on angle, got: {errors}"
