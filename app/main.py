"""
FastAPI 应用入口

配置 FastAPI 应用，注册路由，配置中间件，初始化数据库连接。
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import get_settings
from app.database import init_db, close_db, create_all_tables, get_db_session_context
from app.infra.apimart_client import ApimartClient
from app.infra.task_poller import TaskPoller
from app.models import TaskStatus
from app.repositories import BaseModelTaskRepository, EditTaskRepository, OutfitTaskRepository
from app.routes import models_router, tasks_router
from app.services.polling_callbacks import on_task_completed, on_task_failed, on_task_progress
from app.services.task_query_service import TaskQueryService

logger = logging.getLogger(__name__)


async def _resume_pending_polls(app: FastAPI) -> None:
    """
    启动恢复轮询（一次性）：扫描数据库中 pending 任务并启动轮询。

    说明：只恢复已绑定 `apimart_task_id` 的任务；如果任务尚未提交到 Apimart（apimart_task_id 为空），
    仅靠当前数据库内容无法安全重试提交（需要持久化输入参数/图片）。
    """
    poller: TaskPoller = app.state.task_poller
    settings = get_settings()

    if not settings.resume_polling_on_startup:
        return

    retention_days = settings.apimart_task_retention_days
    cutoff = (
        datetime.now(timezone.utc).replace(tzinfo=None)
        - timedelta(days=retention_days)
    )

    try:
        async with get_db_session_context() as session:
            base_repo = BaseModelTaskRepository(session)
            edit_repo = EditTaskRepository(session)
            outfit_repo = OutfitTaskRepository(session)
            query_service = TaskQueryService(session)

            pending_tasks = [
                *await base_repo.get_pending_tasks(),
                *await edit_repo.get_pending_tasks(),
                *await outfit_repo.get_pending_tasks(),
            ]

            for task in pending_tasks:
                if not task.apimart_task_id:
                    continue

                created_at = task.created_at
                if created_at is not None and created_at.tzinfo is not None:
                    created_at = created_at.replace(tzinfo=None)

                # Apimart 线上只保留近 N 天任务：过期任务不再轮询，直接标记失败，避免无意义请求与日志噪音
                if retention_days and created_at and created_at < cutoff:
                    await query_service.update_status(
                        task.task_id,
                        TaskStatus.FAILED,
                        error_message=(
                            f"Apimart task expired (>{retention_days} days), skip polling; please resubmit"
                        ),
                    )
                    continue

                await poller.start_polling(task.apimart_task_id, local_task_id=task.task_id)

    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.exception(f"Failed to resume pending polls: {exc}")


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

    # 创建应用级单例 ApimartClient/TaskPoller（避免每个请求创建一套资源）
    app.state.apimart_client = ApimartClient()
    app.state.task_poller = TaskPoller(
        apimart_client=app.state.apimart_client,
        on_task_completed=on_task_completed,
        on_task_failed=on_task_failed,
        on_task_progress=on_task_progress,
    )

    # 重启恢复：后台扫描 pending 任务并启动轮询
    app.state.polling_resumer_task = asyncio.create_task(_resume_pending_polls(app))
    
    yield

    # 关闭后台恢复任务
    resumer_task = getattr(app.state, "polling_resumer_task", None)
    if resumer_task is not None:
        resumer_task.cancel()
        try:
            await resumer_task
        except asyncio.CancelledError:
            pass

    # 关闭轮询器（取消活跃轮询并释放 OSS/HTTP 资源）
    poller = getattr(app.state, "task_poller", None)
    if poller is not None:
        await poller.close()
    
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
