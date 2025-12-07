"""
Model Service

业务逻辑层：处理模特生成相关的业务逻辑。
包括默认模特生成、模特编辑、穿搭生成。
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.apimart_client import ApimartClient
from app.models import TaskStatus, TaskType
from app.prompts import (
    build_default_model_prompt,
    build_edit_model_prompt,
    build_outfit_prompt,
)
from app.repositories.task_repository import TaskRepository
from app.schemas import (
    DefaultModelRequest,
    EditModelRequest,
    OutfitModelRequest,
    TaskData,
    TaskResponse,
)


class BaseModelNotFoundError(Exception):
    """基础模特任务不存在异常"""

    def __init__(self, task_id: int):
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
        self.task_repo = TaskRepository(session)
        self.apimart_client = apimart_client or ApimartClient()

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

        Requirements: 1.1, 1.4
        """
        # 1. 创建任务记录
        task = await self.task_repo.create(
            request_id=request.request_id,
            user_id=request.user_id,
            task_type=TaskType.DEFAULT,
        )

        # 2. 构建 Prompt
        prompt = self._build_default_model_prompt(request)

        # 3. 提交到 Apimart
        external_task_id = await self.apimart_client.submit_generation(
            prompt=prompt,
            image_urls=[request.user_image_base64],
        )

        # 4. 更新外部任务 ID
        await self.task_repo.set_external_task_id(task.id, external_task_id)

        # 5. 返回响应
        return TaskResponse(
            code=0,
            msg="accepted",
            data=TaskData(
                task_id=task.id,
                status=TaskStatus.SUBMITTED.value,
            ),
        )

    async def _validate_base_model_task(self, base_model_task_id: int) -> None:
        """
        验证基础模特任务是否存在

        Args:
            base_model_task_id: 基础模特任务 ID

        Raises:
            BaseModelNotFoundError: 基础模特任务不存在
        """
        base_task = await self.task_repo.get_by_id(base_model_task_id)
        if base_task is None:
            raise BaseModelNotFoundError(base_model_task_id)

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

        Requirements: 2.1, 2.2, 2.3
        """
        # 1. 验证基础模特任务存在
        await self._validate_base_model_task(request.base_model_task_id)

        # 2. 创建任务记录
        task = await self.task_repo.create(
            request_id=request.request_id,
            user_id=request.user_id,
            task_type=TaskType.EDIT,
            base_model_task_id=request.base_model_task_id,
        )

        # 3. 构建 Prompt
        prompt = self._build_edit_model_prompt(request)

        # 4. 提交到 Apimart（需要获取基础模特的图片作为输入）
        # 注：实际实现中需要从 image_repository 获取基础模特图片
        external_task_id = await self.apimart_client.submit_generation(
            prompt=prompt,
            image_urls=[],  # TODO: 从基础模特任务获取图片
        )

        # 5. 更新外部任务 ID
        await self.task_repo.set_external_task_id(task.id, external_task_id)

        # 6. 返回响应
        return TaskResponse(
            code=0,
            msg="accepted",
            data=TaskData(
                task_id=task.id,
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
        return build_outfit_prompt(
            angle=request.angle.value,
            outfit_description=request.outfit_description,
        )

    async def create_outfit(self, request: OutfitModelRequest) -> TaskResponse:
        """
        创建穿搭生成任务

        Args:
            request: 穿搭生成请求

        Returns:
            TaskResponse: 任务创建响应

        Raises:
            BaseModelNotFoundError: 基础模特任务不存在

        Requirements: 3.1, 3.2, 3.3, 3.4
        """
        # 1. 验证基础模特任务存在
        await self._validate_base_model_task(request.base_model_task_id)

        # 2. 创建任务记录
        task = await self.task_repo.create(
            request_id=request.request_id,
            user_id=request.user_id,
            task_type=TaskType.OUTFIT,
            base_model_task_id=request.base_model_task_id,
            angle=request.angle.value,
        )

        # 3. 构建 Prompt
        prompt = self._build_outfit_prompt(request)

        # 4. 提交到 Apimart（传入 1-5 张服装单品图片 URL）
        external_task_id = await self.apimart_client.submit_generation(
            prompt=prompt,
            image_urls=request.outfit_image_urls,
        )

        # 5. 更新外部任务 ID
        await self.task_repo.set_external_task_id(task.id, external_task_id)

        # 6. 返回响应
        return TaskResponse(
            code=0,
            msg="accepted",
            data=TaskData(
                task_id=task.id,
                status=TaskStatus.SUBMITTED.value,
                angle=request.angle.value,
            ),
        )
