"""
配置管理模块

使用 Pydantic Settings 管理环境变量配置。
支持从 .env 文件或环境变量加载配置。
"""

import os
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 数据库配置（必须配置 MySQL）
    database_url: str = Field(
        default="",
        description="MySQL 数据库连接 URL (必填)",
    )
    database_echo: bool = Field(
        default=False,
        description="是否打印 SQL 语句",
    )

    @model_validator(mode="after")
    def validate_database_url(self) -> "Settings":
        """验证数据库配置"""
        if not self.database_url:
            raise ValueError("DATABASE_URL 未配置，必须配置 MySQL 数据库连接")
        if not self.database_url.startswith("mysql"):
            raise ValueError("DATABASE_URL 必须是 MySQL 连接 (mysql+aiomysql://...)")
        return self

    # Apimart API 配置
    apimart_api_key: str = Field(
        default="",
        description="Apimart API Key",
    )
    apimart_base_url: str = Field(
        default="https://api.apimart.ai/v1",
        description="Apimart API 基础 URL",
    )
    apimart_model: str = Field(
        default="gemini-3-pro-image-preview",
        description="Apimart 图像生成模型名称",
    )

    # 任务轮询配置
    task_poll_interval: float = Field(
        default=5.0,
        description="任务轮询间隔（秒）",
    )

    # Apimart 任务保留与启动恢复配置
    apimart_task_retention_days: int = Field(
        default=3,
        ge=0,
        description="Apimart 线上任务保留天数（用于启动恢复轮询时过滤过期任务）",
    )
    resume_polling_on_startup: bool = Field(
        default=True,
        description="是否在服务启动时恢复 pending 任务的轮询",
    )

    # API 认证配置
    api_auth_enabled: bool = Field(
        default=False,
        description="是否启用 API 认证（设为 True 开启）",
    )
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

    # 阿里云 OSS 配置
    oss_endpoint: str = Field(
        default="oss-cn-shenzhen.aliyuncs.com",
        description="OSS Endpoint",
    )
    oss_bucket: str = Field(
        default="suitme",
        description="OSS Bucket 名称",
    )
    oss_access_key_id: str = Field(
        default="",
        description="OSS Access Key ID",
    )
    oss_access_key_secret: str = Field(
        default="",
        description="OSS Access Key Secret",
    )


@lru_cache
def get_settings() -> Settings:
    """
    获取应用配置（单例模式）

    Returns:
        Settings: 应用配置实例
    """
    return Settings()
