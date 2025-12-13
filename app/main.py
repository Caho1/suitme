"""
FastAPI 应用入口

配置 FastAPI 应用，注册路由，配置中间件，初始化数据库连接。
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import get_settings
from app.database import init_db, close_db, create_all_tables
from app.routes import models_router, tasks_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    应用生命周期管理
    
    启动时初始化数据库连接，关闭时清理资源。
    """
    settings = get_settings()
    
    # 启动时初始化数据库
    init_db(
        database_url=settings.database_url,
        echo=settings.database_echo,
    )
    
    # 导入模型以确保表定义被注册
    from app.models import BaseModelTask, EditTask, OutfitTask, GenerationImage  # noqa: F401
    
    # 创建数据库表（开发环境）
    await create_all_tables()
    
    yield
    
    # 关闭时清理数据库连接
    await close_db()


# Bearer Token 认证
security = HTTPBearer(auto_error=False)


async def verify_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str | None:
    """
    验证 Bearer Token
    
    Args:
        credentials: HTTP Authorization 头中的凭证
        
    Returns:
        str | None: 验证通过的 token，或 None（认证关闭时）
        
    Raises:
        HTTPException: token 无效时抛出 401 错误
    """
    settings = get_settings()
    
    # 如果认证未启用，直接跳过
    if not settings.api_auth_enabled:
        return None
    
    # 认证已启用，必须提供 token
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail={"code": 1005, "msg": "缺少认证 Token", "data": None},
        )
    
    expected_token = settings.api_auth_token
    if credentials.credentials != expected_token:
        raise HTTPException(
            status_code=401,
            detail={"code": 1005, "msg": "无效的认证 Token", "data": None},
        )
    
    return credentials.credentials


def create_app() -> FastAPI:
    """
    创建 FastAPI 应用实例
    
    Returns:
        FastAPI: 配置完成的应用实例
    """
    app = FastAPI(
        title="Suitme 数字模特图像生成服务",
        description="AI 驱动的数字模特图像生成后端服务，为电商穿搭展示提供支持。",
        version="1.0.0",
        lifespan=lifespan,
    )

    # 配置 CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应限制具体域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由（带认证）
    app.include_router(models_router, dependencies=[Depends(verify_token)])
    app.include_router(tasks_router, dependencies=[Depends(verify_token)])
    
    # 全局异常处理
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """全局异常处理器"""
        return JSONResponse(
            status_code=500,
            content={
                "code": 1004,
                "msg": f"内部错误: {str(exc)}",
                "data": None,
            },
        )
    
    # 健康检查端点
    @app.get("/health", tags=["health"])
    async def health_check() -> dict:
        """健康检查"""
        return {"status": "healthy"}
    
    # 测试页面
    @app.get("/test", include_in_schema=False)
    async def test_page() -> FileResponse:
        """返回测试页面"""
        return FileResponse("test.html")
    
    return app


# 创建应用实例
app = create_app()
