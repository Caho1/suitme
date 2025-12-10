"""
Model Service

业务逻辑层：处理模特生成相关的业务逻辑。
包括默认模特生成、模特编辑、穿搭生成。
"""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

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
            session: 数据库会话
            apimart_client: Apimart 客户端（可选，用于测试注入）
        """
        self.session = session
        self.base_model_repo = BaseModelTaskRepository(session)
        self.edit_repo = EditTaskRepository(session)
        self.outfit_repo = OutfitTaskRepository(session)
        self.image_repo = ImageRepository(session)
        self.query_service = TaskQueryService(session)
        self.apimart_client = apimart_client or ApimartClient()
        self._poller = TaskPoller(
            apimart_client=self.apimart_client,
            on_task_completed=self._handle_task_completed,
            on_task_failed=self._handle_task_failed,
            on_task_progress=self._handle_task_progress,
        )

    async def _handle_task_progress(
        self, task_id: str, status: TaskStatus, progress: int
    ) -> None:
        """处理任务进度更新 - 使用 TaskQueryService 统一更新"""
        await self.query_service.update_status(task_id, TaskStatus.PROCESSING, progress)
        await self.session.commit()

    async def _handle_task_completed(
        self, task_id: str, image_base64: str | None, image_url: str | None
    ) -> None:
        """处理任务完成 - 使用 TaskQueryService 统一更新"""
        result = await self.query_service.update_status(task_id, TaskStatus.COMPLETED, 100)
        if result:
            await self.image_repo.create(
                task_type=result.task_type,
                task_id=result.id,
                angle=result.angle,
                image_base64=image_base64,
                image_url=image_url,
            )
        await self.session.commit()

    async def _handle_task_failed(self, task_id: str, error_message: str) -> None:
        """处理任务失败 - 使用 TaskQueryService 统一更新"""
        await self.query_service.update_status(
            task_id, TaskStatus.FAILED, error_message=error_message
        )
        await self.session.commit()

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
            height_cm=profile.height_cm,
            weight_kg=profile.weight_kg,
            age=profile.age,
            skin_tone=profile.skin_tone,
            body_shape=profile.body_shape,
        )

    async def create_default_model(
        self,
        request: DefaultModelRequest,
    ) -> TaskResponse:
        """
        创建默认模特生成任务

        Args:
            request: 默认模特请求

        Returns:
            TaskResponse: 任务创建响应

        Requirements: 2.1, 3.1
        """
        # 1. 构建 Prompt
        prompt = self._build_default_model_prompt(request)

        # 2. 提交到 Apimart，获取 task_id
        task_id = await self.apimart_client.submit_generation(
            prompt=prompt,
            image_urls=[request.user_image],
            size=request.size.value,
        )

        # 3. 创建任务记录（使用 Apimart 返回的 task_id，存储 body_profile 字段）
        profile = request.body_profile
        task = await self.base_model_repo.create(
            task_id=task_id,
            request_id=request.request_id,
            user_id=request.user_id,
            gender=profile.gender,
            height_cm=profile.height_cm,
            weight_kg=profile.weight_kg,
            age=profile.age,
            skin_tone=profile.skin_tone,
            body_shape=profile.body_shape,
        )
        await self.session.commit()

        # 4. 启动后台轮询
        asyncio.create_task(self._poller.start_polling(task_id))

        # 5. 返回响应
        return TaskResponse(
            code=0,
            msg="accepted",
            data=TaskData(
                task_id=task_id,
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
        
        # 优先使用 base64，否则使用 URL
        image_data = image.image_base64 or image.image_url
        if not image_data:
            raise BaseModelNotFoundError(f"{base_model_task_id} (no image data)")
        
        return base_task.id, image_data

    def _build_edit_model_prompt(self, request: EditModelRequest) -> str:
        """
        构建模特编辑的 Prompt

        Args:
            request: 模特编辑请求

        Returns:
            str: 编辑 Prompt
        """
        return build_edit_model_prompt(request.edit_instructions)

    async def edit_model(self, request: EditModelRequest) -> TaskResponse:
        """
        创建模特编辑任务

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

        # 2. 构建 Prompt
        prompt = self._build_edit_model_prompt(request)

        # 3. 提交到 Apimart，获取 task_id
        task_id = await self.apimart_client.submit_generation(
            prompt=prompt,
            image_urls=[base_image],
            size=request.size.value,
        )

        # 4. 创建任务记录（使用 EditTaskRepository）
        task = await self.edit_repo.create(
            task_id=task_id,
            request_id=request.request_id,
            user_id=request.user_id,
            base_model_id=base_internal_id,
            edit_instructions=request.edit_instructions,
        )
        await self.session.commit()

        # 5. 启动后台轮询
        asyncio.create_task(self._poller.start_polling(task_id))

        # 6. 返回响应
        return TaskResponse(
            code=0,
            msg="accepted",
            data=TaskData(
                task_id=task_id,
                status=TaskStatus.SUBMITTED.value,
            ),
        )

    def _build_outfit_prompt(self, request: OutfitModelRequest) -> str:
        """
        构建穿搭生成的 Prompt

        Args:
            request: 穿搭生成请求

        Returns:
            str: 穿搭 Prompt
        """
        return build_outfit_prompt(angle=request.angle.value)

    async def create_outfit(self, request: OutfitModelRequest) -> TaskResponse:
        """
        创建穿搭生成任务

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

        # 2. 构建 Prompt
        prompt = self._build_outfit_prompt(request)

        # 3. 提交到 Apimart，获取 task_id（基础模特图片 + 服装图片）
        task_id = await self.apimart_client.submit_generation(
            prompt=prompt,
            image_urls=[base_image] + request.outfit_images,
            size=request.size.value,
        )

        # 4. 创建任务记录（使用 OutfitTaskRepository）
        task = await self.outfit_repo.create(
            task_id=task_id,
            request_id=request.request_id,
            user_id=request.user_id,
            base_model_id=base_internal_id,
            angle=request.angle.value,
        )
        await self.session.commit()

        # 5. 启动后台轮询
        asyncio.create_task(self._poller.start_polling(task_id))

        # 6. 返回响应
        return TaskResponse(
            code=0,
            msg="accepted",
            data=TaskData(
                task_id=task_id,
                status=TaskStatus.SUBMITTED.value,
                angle=request.angle.value,
            ),
        )
