# Design Document: Code Refactoring

## Overview

本设计文档描述了 Suitme 项目的代码重构方案，目标是消除重复代码、降低嵌套深度、提高可维护性，同时确保现有功能完全不受影响。

重构采用渐进式策略：
1. 先创建新的基础设施（泛型基类、统一方法）
2. 逐步迁移现有代码使用新基础设施
3. 保留原有接口签名，确保向后兼容

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Services Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ModelService │  │TaskService  │  │PollingService       │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                     │             │
│         └────────────────┼─────────────────────┘             │
│                          ▼                                   │
│              ┌───────────────────────┐                       │
│              │  TaskQueryService     │  ◄── 统一查询和更新   │
│              │  + find_by_task_id()  │                       │
│              │  + update_status()    │  ◄── 新增统一更新方法 │
│              │  + _get_repo_by_type()│                       │
│              └───────────┬───────────┘                       │
└──────────────────────────┼───────────────────────────────────┘
                           │
┌──────────────────────────┼───────────────────────────────────┐
│                          ▼                                   │
│              ┌───────────────────────┐                       │
│              │  BaseTaskRepository   │  ◄── 新增泛型基类     │
│              │  (Generic[T])         │                       │
│              └───────────┬───────────┘                       │
│         ┌────────────────┼────────────────┐                  │
│         ▼                ▼                ▼                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │BaseModel    │  │EditTask     │  │OutfitTask   │          │
│  │TaskRepo     │  │Repository   │  │Repository   │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│                    Repositories Layer                        │
└──────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. BaseTaskRepository (新增)

泛型基类，封装所有任务 Repository 的通用 CRUD 操作。

```python
from typing import TypeVar, Generic, Type
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import Base

T = TypeVar("T", bound=Base)

class BaseTaskRepository(Generic[T]):
    """任务 Repository 泛型基类"""
    
    model: Type[T]  # 子类必须定义
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, id: int) -> T | None:
        """根据内部 ID 获取任务"""
        ...
    
    async def get_by_task_id(self, task_id: str) -> T | None:
        """根据 Apimart task_id 获取任务"""
        ...
    
    async def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress: int | None = None,
        error_message: str | None = None,
    ) -> T | None:
        """更新任务状态"""
        ...
    
    async def get_pending_tasks(self) -> list[T]:
        """获取待处理任务"""
        ...
```

### 2. TaskQueryService (扩展)

扩展现有的 TaskQueryService，添加统一的状态更新方法。

```python
class TaskQueryService:
    """统一任务查询服务"""
    
    # 现有方法保持不变
    async def find_by_task_id(self, task_id: str) -> TaskQueryResult | None: ...
    async def exists(self, task_id: str) -> bool: ...
    
    # 新增方法
    def _get_repo_by_type(self, task_type: TaskType) -> BaseTaskRepository:
        """根据任务类型返回对应的 repository"""
        ...
    
    async def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress: int | None = None,
        error_message: str | None = None,
    ) -> TaskQueryResult | None:
        """统一的状态更新方法"""
        ...
```

### 3. TaskPoller (优化)

提取错误消息解析为独立方法。

```python
class TaskPoller:
    # 新增方法
    @staticmethod
    def _extract_error_message(error: str | dict | None) -> str:
        """从 Apimart 错误响应中提取错误消息"""
        if isinstance(error, dict):
            return error.get("message", str(error))
        return str(error) if error else "Unknown error from Apimart"
```

### 4. CallbackPayload (优化)

使用字典推导式简化 `to_dict` 方法。

```python
@dataclass
class CallbackPayload:
    def to_dict(self) -> dict[str, Any]:
        """转换为字典，排除 None 值"""
        return {
            k: v for k, v in {
                "task_id": self.task_id,
                "status": self.status,
                "type": self.type,
                "angle": self.angle,
                "image_base64": self.image_base64,
                "image_url": self.image_url,
                "error_message": self.error_message,
            }.items() if v is not None
        }
```

## Data Models

数据模型保持不变，重构不涉及数据库结构变更。

现有模型：
- `BaseModelTask` - 模特生成任务
- `EditTask` - 模特编辑任务
- `OutfitTask` - 穿搭生成任务
- `GenerationImage` - 生成图片

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Unified update routes to correct repository
*For any* task type (MODEL, EDIT, OUTFIT) and valid task ID, calling `TaskQueryService.update_status` should update the task in the correct repository and return a TaskQueryResult with matching task_type.
**Validates: Requirements 1.1, 1.2, 1.4**

### Property 2: Base repository methods work for all subclasses
*For any* repository subclass (BaseModelTaskRepository, EditTaskRepository, OutfitTaskRepository), calling inherited methods (`get_by_id`, `get_by_task_id`, `update_status`, `get_pending_tasks`) should operate on the correct model class.
**Validates: Requirements 2.1, 2.3**

### Property 3: Error message extraction handles all formats
*For any* error value (string, dict with "message" key, dict without "message" key, None), `_extract_error_message` should return a non-empty string.
**Validates: Requirements 4.1**

### Property 4: CallbackPayload to_dict filters None values
*For any* CallbackPayload instance with arbitrary None/non-None field combinations, `to_dict()` should return a dictionary containing only non-None values, and always include required fields (task_id, status, type).
**Validates: Requirements 4.2**

### Property 5: API response format unchanged
*For any* valid API request to `/models/default`, `/models/edit`, `/models/outfit`, or `/tasks/{task_id}`, the response structure (field names, types, nesting) should be identical before and after refactoring.
**Validates: Requirements 3.4, 5.3**

### Property 6: Database operations maintain data integrity
*For any* sequence of task creation and status update operations, the final database state should be consistent (no orphaned records, correct foreign key relationships, valid status values).
**Validates: Requirements 5.4**

## Error Handling

重构不改变现有的错误处理策略：

1. **TaskNotFoundError** - 任务不存在时抛出
2. **InvalidStatusTransitionError** - 无效状态转换时抛出
3. **BaseModelNotFoundError** - 基础模特不存在时抛出

新增的 `TaskQueryService.update_status` 方法在任务不存在时返回 `None`，由调用方决定是否抛出异常。

## Testing Strategy

### 单元测试

- 测试 `BaseTaskRepository` 各方法的正确性
- 测试 `TaskQueryService.update_status` 的路由逻辑
- 测试 `_extract_error_message` 的各种输入情况
- 测试 `CallbackPayload.to_dict` 的 None 过滤

### 属性测试

使用 **hypothesis** 库进行属性测试：

- 配置每个属性测试运行至少 100 次迭代
- 每个属性测试必须标注对应的 correctness property
- 格式：`**Feature: code-refactoring, Property {number}: {property_text}**`

### 回归测试

- 运行所有现有测试确保不破坏功能
- 验证 API 响应格式与重构前一致
