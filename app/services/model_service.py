"""
Model Service

业务逻辑层：处理模特生成相关的业务逻辑。
包括默认模特生成、模特编辑、穿搭生成。
"""

import asyncio
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session_context
from app.infra.apimart_client import ApimartClient
from app.infra.task_poller import TaskPoller
from app.models import TaskStatus, TaskType
from app.prompts import (
    build_default_model_prompt,
    build_edit_model_prompt,
    build_outfit_prompt,
)
from app.repositories import (
    BaseModelTaskRepository,
    EditTaskRepository,
    OutfitTaskRepository,
    ImageRepository,
)
from app.schemas import (
    DefaultModelRequest,
    EditModelRequest,
    OutfitModelRequest,
    TaskData,
    TaskResponse,
)
from app.services.task_query_service import TaskQueryService

logger = logging.getLogger(__name__)


class BaseModelNotFoundError(Exception):
    """基础模特任务不存在异常"""

    def __init__(self, task_id: str):
        self.task_id = task_id
        super().__init__(f"Base model task not found: {task_id}")


class ModelService:
    """模特生成服务"""

    def __init__(
        self,
        session: AsyncSession,
        apimart_client: ApimartClient | None = None,
    ):
        """
        初始化模特服务

        Args:
            session: 数据库会话（仅用于请求范围内的操作）
            apimart_client: Apimart 客户端（可选，用于测试注入）
        """
        self.session = session
        self.base_model_repo = BaseModelTaskRepository(session)
        self.edit_repo = EditTaskRepository(session)
        self.outfit_repo = OutfitTaskRepository(session)
        self.image_repo = ImageRepository(session)
        self.query_service = TaskQueryService(session)
        self.apimart_client = apimart_client or ApimartClient()
        # TaskPoller 的回调会在独立会话中执行
        self._poller = TaskPoller(
            apimart_client=self.apimart_client,
            on_task_completed=self._handle_task_completed,
            on_task_failed=self._handle_task_failed,
            on_task_progress=self._handle_task_progress,
        )

    # ========== 回调函数：使用独立会话 ==========

    async def _handle_task_progress(
        self, task_id: str, status: TaskStatus, progress: int
    ) -> None:
        """处理任务进度更新 - 使用独立数据库会话"""
        try:
            async with get_db_session_context() as session:
                query_service = TaskQueryService(session)
                await query_service.update_status(task_id, TaskStatus.PROCESSING, progress)
        except Exception as e:
            logger.exception(f"Failed to update progress for task {task_id}: {e}")

    async def _handle_task_completed(
        self, task_id: str, oss_url: str | None
    ) -> None:
        """处理任务完成 - 使用独立数据库会话"""
        try:
            async with get_db_session_context() as session:
                query_service = TaskQueryService(session)
                image_repo = ImageRepository(session)
                result = await query_service.update_status(task_id, TaskStatus.COMPLETED, 100)
                if result:
                    await image_repo.create(
                        task_type=result.task_type,
                        task_id=result.id,
                        angle=result.angle,
                        image_url=oss_url,
                    )
        except Exception as e:
            logger.exception(f"Failed to handle task completion for {task_id}: {e}")

    async def _handle_task_failed(self, task_id: str, error_message: str) -> None:
        """处理任务失败 - 使用独立数据库会话"""
        try:
            async with get_db_session_context() as session:
                query_service = TaskQueryService(session)
                await query_service.update_status(
                    task_id, TaskStatus.FAILED, error_message=error_message
                )
        except Exception as e:
            logger.exception(f"Failed to handle task failure for {task_id}: {e}")

    # ========== Prompt 构建方法 ==========

    def _build_default_model_prompt(self, request: DefaultModelRequest) -> str:
        """
        构建默认模特生成的 Prompt

        Args:
            request: 默认模特请求

        Returns:
            str: 生成 Prompt
        """
        profile = request.body_profile
        return build_default_model_prompt(
            gender=profile.gender,
            height=profile.height,
            weight=profile.weight,
            age=profile.age,
            skin_color=profile.skin_color,
            body_type=profile.body_type,
        )

    def _build_edit_model_prompt(self, request: EditModelRequest) -> str:
        """
        构建模特编辑的 Prompt

        Args:
            request: 模特编辑请求

        Returns:
            str: 编辑 Prompt
        """
        return build_edit_model_prompt(request.edit_instructions)

    def _build_outfit_prompt(self, request: OutfitModelRequest) -> str:
        """
        构建穿搭生成的 Prompt

        Args:
            request: 穿搭生成请求

        Returns:
            str: 穿搭 Prompt
        """
        return build_outfit_prompt(angle=request.angle.value)

    # ========== 请求处理方法 ==========

    async def create_default_model(
        self,
        request: DefaultModelRequest,
    ) -> TaskResponse:
        """
        创建默认模特生成任务（秒级返回）

        Args:
            request: 默认模特请求

        Returns:
            TaskResponse: 任务创建响应

        Requirements: 2.1, 3.1
        """
        # 1. 生成本地 task_id，立即创建数据库记录
        local_task_id = f"task_{uuid.uuid4().hex[:16]}"
        profile = request.body_profile
        request_id = str(uuid.uuid4())
        
        task = await self.base_model_repo.create(
            task_id=local_task_id,
            request_id=request_id,
            user_id=request.user_id,
            gender=profile.gender,
            height=profile.height,
            weight=profile.weight,
            age=profile.age,
            skin_color=profile.skin_color,
            body_type=profile.body_type,
        )
        await self.session.commit()

        # 2. 后台异步提交到 Apimart 并启动轮询
        asyncio.create_task(
            self._submit_and_poll_default_model(local_task_id, request)
        )

        # 3. 立即返回响应
        return TaskResponse(
            code=0,
            msg="accepted",
            data=TaskData(
                task_id=local_task_id,
                status=TaskStatus.SUBMITTED.value,
            ),
        )

    async def _get_base_model_image(self, base_model_task_id: str) -> tuple[int, str]:
        """
        获取基础模特任务的图片

        Args:
            base_model_task_id: 基础模特任务 ID (Apimart task_id)

        Returns:
            tuple[int, str]: (内部数据库 ID, 图片 base64 或 URL)

        Raises:
            BaseModelNotFoundError: 基础模特任务不存在或没有图片
        """
        base_task = await self.base_model_repo.get_by_task_id(base_model_task_id)
        if base_task is None:
            raise BaseModelNotFoundError(base_model_task_id)
        
        # 获取基础模特的图片
        image = await self.image_repo.get_by_task(TaskType.MODEL, base_task.id)
        if image is None:
            raise BaseModelNotFoundError(f"{base_model_task_id} (no image)")
        
        # 使用 OSS URL
        image_data = image.image_url
        if not image_data:
            raise BaseModelNotFoundError(f"{base_model_task_id} (no image data)")
        
        return base_task.id, image_data

    async def edit_model(self, request: EditModelRequest) -> TaskResponse:
        """
        创建模特编辑任务（秒级返回）

        Args:
            request: 模特编辑请求

        Returns:
            TaskResponse: 任务创建响应

        Raises:
            BaseModelNotFoundError: 基础模特任务不存在

        Requirements: 2.2, 3.2
        """
        # 1. 获取基础模特图片（验证 base_model_id 存在）
        base_internal_id, base_image = await self._get_base_model_image(request.base_model_task_id)

        # 2. 生成本地 task_id，立即创建数据库记录
        local_task_id = f"task_{uuid.uuid4().hex[:16]}"
        request_id = str(uuid.uuid4())
        
        task = await self.edit_repo.create(
            task_id=local_task_id,
            request_id=request_id,
            user_id=request.user_id,
            base_model_id=base_internal_id,
            edit_instructions=request.edit_instructions,
        )
        await self.session.commit()

        # 3. 后台异步提交到 Apimart 并启动轮询
        asyncio.create_task(
            self._submit_and_poll_edit_model(local_task_id, request, base_image)
        )

        # 4. 立即返回响应
        return TaskResponse(
            code=0,
            msg="accepted",
            data=TaskData(
                task_id=local_task_id,
                status=TaskStatus.SUBMITTED.value,
            ),
        )

    async def create_outfit(self, request: OutfitModelRequest) -> TaskResponse:
        """
        创建穿搭生成任务（秒级返回）

        Args:
            request: 穿搭生成请求

        Returns:
            TaskResponse: 任务创建响应

        Raises:
            BaseModelNotFoundError: 基础模特任务不存在

        Requirements: 2.3, 3.3
        """
        # 1. 获取基础模特图片（验证 base_model_id 存在）
        base_internal_id, base_image = await self._get_base_model_image(request.base_model_task_id)

        # 2. 生成本地 task_id，立即创建数据库记录
        local_task_id = f"task_{uuid.uuid4().hex[:16]}"
        request_id = str(uuid.uuid4())
        
        task = await self.outfit_repo.create(
            task_id=local_task_id,
            request_id=request_id,
            user_id=request.user_id,
            base_model_id=base_internal_id,
            angle=request.angle.value,
        )
        await self.session.commit()

        # 3. 后台异步提交到 Apimart 并启动轮询
        asyncio.create_task(
            self._submit_and_poll_outfit(local_task_id, request, base_image)
        )

        # 4. 立即返回响应
        return TaskResponse(
            code=0,
            msg="accepted",
            data=TaskData(
                task_id=local_task_id,
                status=TaskStatus.SUBMITTED.value,
                angle=request.angle.value,
            ),
        )

    # ========== 后台提交函数：使用独立会话 ==========

    async def _submit_and_poll_default_model(
        self, local_task_id: str, request: DefaultModelRequest
    ) -> None:
        """后台异步提交默认模特任务到 Apimart - 使用独立数据库会话"""
        try:
            prompt = self._build_default_model_prompt(request)
            apimart_task_id = await self.apimart_client.submit_generation(
                prompt=prompt,
                image_urls=[request.picture_url],
                size=request.size.value,
            )
            # 使用独立会话更新 apimart_task_id
            async with get_db_session_context() as session:
                repo = BaseModelTaskRepository(session)
                await repo.update_apimart_task_id(local_task_id, apimart_task_id)
            # 启动轮询
            await self._poller.start_polling(apimart_task_id, local_task_id)
        except Exception as e:
            logger.exception(f"Failed to submit task {local_task_id}: {e}")
            async with get_db_session_context() as session:
                query_service = TaskQueryService(session)
                await query_service.update_status(
                    local_task_id, TaskStatus.FAILED, error_message=f"Apimart 调用失败: {str(e)}"
                )

    async def _submit_and_poll_edit_model(
        self, local_task_id: str, request: EditModelRequest, base_image: str
    ) -> None:
        """后台异步提交编辑任务到 Apimart - 使用独立数据库会话"""
        try:
            prompt = self._build_edit_model_prompt(request)
            apimart_task_id = await self.apimart_client.submit_generation(
                prompt=prompt,
                image_urls=[base_image],
                size=request.size.value,
            )
            # 使用独立会话更新 apimart_task_id
            async with get_db_session_context() as session:
                repo = EditTaskRepository(session)
                await repo.update_apimart_task_id(local_task_id, apimart_task_id)
            # 启动轮询
            await self._poller.start_polling(apimart_task_id, local_task_id)
        except Exception as e:
            logger.exception(f"Failed to submit task {local_task_id}: {e}")
            async with get_db_session_context() as session:
                query_service = TaskQueryService(session)
                await query_service.update_status(
                    local_task_id, TaskStatus.FAILED, error_message=f"Apimart 调用失败: {str(e)}"
                )

    async def _submit_and_poll_outfit(
        self, local_task_id: str, request: OutfitModelRequest, base_image: str
    ) -> None:
        """后台异步提交穿搭任务到 Apimart - 使用独立数据库会话"""
        try:
            prompt = self._build_outfit_prompt(request)
            apimart_task_id = await self.apimart_client.submit_generation(
                prompt=prompt,
                image_urls=[base_image] + request.outfit_images,
                size=request.size.value,
            )
            # 使用独立会话更新 apimart_task_id
            async with get_db_session_context() as session:
                repo = OutfitTaskRepository(session)
                await repo.update_apimart_task_id(local_task_id, apimart_task_id)
            # 启动轮询
            await self._poller.start_polling(apimart_task_id, local_task_id)
        except Exception as e:
            logger.exception(f"Failed to submit task {local_task_id}: {e}")
            async with get_db_session_context() as session:
                query_service = TaskQueryService(session)
                await query_service.update_status(
                    local_task_id, TaskStatus.FAILED, error_message=f"Apimart 调用失败: {str(e)}"
                )
