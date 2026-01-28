"""
Models API Routes

处理模特生成相关的 HTTP 请求：
- POST /models/default - 创建默认模特
- POST /models/edit - 编辑模特
- POST /models/outfit - 穿搭生成
"""

from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.schemas import (
    DefaultModelRequest,
    EditModelRequest,
    OutfitModelRequest,
    TaskResponse,
    ErrorResponse,
)
from app.services.model_service import ModelService, BaseModelNotFoundError


router = APIRouter(prefix="/models", tags=["models"])


def raise_base_model_not_found(task_id: str) -> NoReturn:
    """抛出基础模特不存在的 HTTP 异常"""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": 1003, "msg": f"基础模特任务不存在: {task_id}", "data": None},
    )


def get_model_service(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> ModelService:
    """依赖注入：获取 ModelService 实例"""
    # 优先使用应用级单例 poller，避免每个请求创建一套轮询与 OSS/HTTP 资源
    task_poller = getattr(request.app.state, "task_poller", None)
    apimart_client = getattr(request.app.state, "apimart_client", None)
    return ModelService(session, apimart_client=apimart_client, task_poller=task_poller)


@router.post(
    "/default",
    response_model=TaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse, "description": "参数错误"},
        500: {"model": ErrorResponse, "description": "内部错误"},
    },
)
async def create_default_model(
    request: DefaultModelRequest,
    service: ModelService = Depends(get_model_service),
) -> TaskResponse:
    """
    创建默认模特生成任务

    Requirements: 1.1, 1.2, 1.3
    """
    return await service.create_default_model(request)


@router.post(
    "/edit",
    response_model=TaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse, "description": "参数错误"},
        404: {"model": ErrorResponse, "description": "基础模特不存在"},
        500: {"model": ErrorResponse, "description": "内部错误"},
    },
)
async def edit_model(
    request: EditModelRequest,
    service: ModelService = Depends(get_model_service),
) -> TaskResponse:
    """
    创建模特编辑任务

    Requirements: 2.1, 2.2
    """
    try:
        return await service.edit_model(request)
    except BaseModelNotFoundError as e:
        raise_base_model_not_found(e.task_id)


@router.post(
    "/outfit",
    response_model=TaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse, "description": "参数错误"},
        404: {"model": ErrorResponse, "description": "基础模特不存在"},
        500: {"model": ErrorResponse, "description": "内部错误"},
    },
)
async def create_outfit(
    request: OutfitModelRequest,
    service: ModelService = Depends(get_model_service),
) -> TaskResponse:
    """
    创建穿搭生成任务

    Requirements: 3.1, 3.2, 3.3
    """
    try:
        return await service.create_outfit(request)
    except BaseModelNotFoundError as e:
        raise_base_model_not_found(e.task_id)
