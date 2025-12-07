"""
配置管理模块

使用 Pydantic Settings 管理环境变量配置。
支持从 .env 文件或环境变量加载配置。
"""

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 数据库配置
    database_url: str = Field(
        default="mysql+aiomysql://root:123456@localhost:3306/suitme",
        description="数据库连接 URL",
    )
    database_echo: bool = Field(
        default=False,
        description="是否打印 SQL 语句",
    )

    # Apimart API 配置
    apimart_api_key: str = Field(
        default="",
        description="Apimart API Key",
    )
    apimart_base_url: str = Field(
        default="https://api.apimart.ai/v1",
        description="Apimart API 基础 URL",
    )

    # 任务轮询配置
    task_poll_interval: float = Field(
        default=2.0,
        description="任务轮询间隔（秒）",
    )
    task_timeout: float = Field(
        default=120.0,
        description="任务超时时间（秒）",
    )

    # API 认证配置
    api_auth_token: str = Field(
        default="",
        description="API 接口认证 Token（Bearer Token）",
    )

    # 回调配置
    callback_url: str = Field(
        default="",
        description="Java 后端回调 URL",
    )
    callback_token: str = Field(
        default="",
        description="回调请求身份验证 Token",
    )
    callback_max_retries: int = Field(
        default=3,
        description="回调最大重试次数",
    )

    # HTTP 客户端配置
    http_timeout: float = Field(
        default=30.0,
        description="HTTP 请求超时时间（秒）",
    )

    # 重试配置
    retry_max_attempts: int = Field(
        default=5,
        description="最大重试次数",
    )
    retry_base_delay: float = Field(
        default=1.0,
        description="重试基础延迟（秒）",
    )
    retry_max_delay: float = Field(
        default=32.0,
        description="重试最大延迟（秒）",
    )


@lru_cache
def get_settings() -> Settings:
    """
    获取应用配置（单例模式）

    Returns:
        Settings: 应用配置实例
    """
    return Settings()
