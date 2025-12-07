"""
Tasks API Routes

处理任务状态查询相关的 HTTP 请求：
- GET /tasks/{task_id} - 查询任务状态
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.schemas import TaskStatusResponse, ErrorResponse
from app.services.task_service import TaskService, TaskNotFoundError


router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_task_service(session: AsyncSession = Depends(get_db_session)) -> TaskService:
    """依赖注入：获取 TaskService 实例"""
    return TaskService(session)


@router.get(
    "/{task_id}",
    response_model=TaskStatusResponse,
    responses={
        404: {"model": ErrorResponse, "description": "任务不存在"},
        500: {"model": ErrorResponse, "description": "内部错误"},
    },
)
async def get_task_status(
    task_id: int,
    service: TaskService = Depends(get_task_service),
) -> TaskStatusResponse:
    """
    查询任务状态
    
    Requirements: 5.1, 5.2, 5.3
    """
    try:
        return await service.get_task_status(task_id)
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": 1003, "msg": f"任务不存在: {task_id}", "data": None},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": 1004, "msg": f"内部错误: {str(e)}", "data": None},
        )
