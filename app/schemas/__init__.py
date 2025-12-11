"""
Pydantic Request/Response Schemas

定义 API 请求体和响应体的数据结构。
包含数据验证逻辑，确保输入数据符合业务规则。
"""

import base64
import re
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ============== 枚举类型 ==============

class AngleType(str, Enum):
    """视角枚举"""
    FRONT = "front"
    SIDE = "side"
    BACK = "back"


class ImageSize(str, Enum):
    """图片尺寸比例枚举"""
    RATIO_1_1 = "1:1"
    RATIO_2_3 = "2:3"
    RATIO_3_2 = "3:2"
    RATIO_3_4 = "3:4"
    RATIO_4_3 = "4:3"
    RATIO_4_5 = "4:5"
    RATIO_5_4 = "5:4"
    RATIO_9_16 = "9:16"
    RATIO_16_9 = "16:9"
    RATIO_21_9 = "21:9"


# ============== 通用模型 ==============

class BodyProfile(BaseModel):
    """用户身体参数 (所有字段可选)"""
    gender: Literal["male", "female"] | None = Field(default=None, description="性别")
    height_cm: float | None = Field(default=None, gt=0, le=300, description="身高 (cm)")
    weight_kg: float | None = Field(default=None, gt=0, le=500, description="体重 (kg)")
    age: int | None = Field(default=None, gt=0, le=150, description="年龄")
    skin_tone: str | None = Field(default=None, min_length=1, description="肤色")
    body_shape: str | None = Field(default=None, description="身材类型")


# ============== 图片验证 ==============

# Data URI 格式: data:[<mediatype>][;base64],<data>
DATA_URI_PATTERN = re.compile(
    r"^data:image/(jpeg|jpg|png|gif|webp|bmp);base64,[A-Za-z0-9+/]+=*$"
)

# URL 格式: http:// 或 https:// 开头
URL_PATTERN = re.compile(r"^https?://")


def is_valid_url(value: str) -> bool:
    """检查字符串是否为有效的 URL"""
    return bool(URL_PATTERN.match(value))


def is_valid_data_uri(value: str) -> bool:
    """检查字符串是否为有效的 Data URI 格式"""
    if not DATA_URI_PATTERN.match(value):
        return False
    try:
        base64_part = value.split(",", 1)[1]
        base64.b64decode(base64_part, validate=True)
        return True
    except Exception:
        return False


def validate_image_input(value: str) -> str:
    """
    验证图片输入，支持 Data URI 或 URL
    
    Args:
        value: 待验证的字符串 (Data URI 或 URL)
        
    Returns:
        验证通过的原始字符串
        
    Raises:
        ValueError: 格式不符合要求
    """
    if not value:
        raise ValueError("图片数据不能为空")
    
    # 支持 URL 格式
    if is_valid_url(value):
        return value
    
    # 支持 Data URI 格式
    if is_valid_data_uri(value):
        return value
    
    raise ValueError(
        "图片必须是有效的 URL (http/https) 或 Data URI 格式 (data:image/<type>;base64,<data>)"
    )


# ============== 请求模型 ==============

class DefaultModelRequest(BaseModel):
    """默认模特生成请求"""
    user_id: str = Field(..., min_length=1, description="用户 ID")
    user_image: str = Field(..., description="用户正面照片 (支持 Data URI 或 URL)")
    body_profile: BodyProfile = Field(..., description="用户身体参数")
    size: ImageSize = Field(default=ImageSize.RATIO_4_3, description="生成图片比例")

    @field_validator("user_image")
    @classmethod
    def validate_user_image(cls, v: str) -> str:
        return validate_image_input(v)


class EditModelRequest(BaseModel):
    """模特编辑请求"""
    user_id: str = Field(..., min_length=1, description="用户 ID")
    base_model_task_id: str = Field(..., min_length=1, description="基础模特任务 ID (格式: task_xxxxxxx)")
    edit_instructions: str = Field(..., min_length=1, description="编辑指令")
    size: ImageSize = Field(default=ImageSize.RATIO_4_3, description="生成图片比例")


class OutfitModelRequest(BaseModel):
    """穿搭生成请求"""
    user_id: str = Field(..., min_length=1, description="用户 ID")
    base_model_task_id: str = Field(..., min_length=1, description="基础模特任务 ID (格式: task_xxxxxxx)")
    angle: AngleType = Field(..., description="视角: front/side/back")
    outfit_images: list[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="服装单品图片列表 (1-5 张，支持 Data URI 或 URL)",
    )
    size: ImageSize = Field(default=ImageSize.RATIO_4_3, description="生成图片比例")

    @field_validator("outfit_images")
    @classmethod
    def validate_outfit_images(cls, v: list[str]) -> list[str]:
        """验证图片列表，每个元素必须是有效的 URL 或 Data URI"""
        for img in v:
            validate_image_input(img)
        return v


# ============== 响应模型 ==============

class TaskData(BaseModel):
    """任务数据"""
    task_id: str = Field(..., description="任务 ID (格式: task_xxxxxxx)")
    status: str = Field(..., description="任务状态")
    angle: str | None = Field(default=None, description="视角 (仅穿搭任务)")


class TaskResponse(BaseModel):
    """任务创建响应"""
    code: int = Field(default=0, description="响应码，0 表示成功")
    msg: str = Field(default="accepted", description="响应消息")
    data: TaskData = Field(..., description="任务数据")


class ImageData(BaseModel):
    """图片数据"""
    image_base64: str | None = Field(default=None, description="图片 Base64")
    image_url: str | None = Field(default=None, description="图片 OSS URL")


class TaskStatusData(BaseModel):
    """任务状态数据"""
    task_id: str = Field(..., description="任务 ID (格式: task_xxxxxxx)")
    status: str = Field(..., description="任务状态")
    progress: int = Field(default=0, description="进度百分比")
    type: str = Field(..., description="任务类型")
    angle: str | None = Field(default=None, description="视角")
    image: ImageData | None = Field(default=None, description="图片信息 (已完成时)")
    error_message: str | None = Field(default=None, description="错误信息 (失败时)")


class TaskStatusResponse(BaseModel):
    """任务状态查询响应"""
    code: int = Field(default=0, description="响应码")
    msg: str = Field(default="success", description="响应消息")
    data: TaskStatusData = Field(..., description="任务状态数据")


class ErrorResponse(BaseModel):
    """错误响应"""
    code: int = Field(..., description="错误码")
    msg: str = Field(..., description="错误消息")
    data: None = Field(default=None, description="无数据")
