# Requirements Document

## Introduction

本文档定义了 Suitme 项目代码重构的需求规范。重构目标是消除重复代码、降低嵌套深度、提高代码可维护性，同时确保现有功能完全不受影响。重构遵循单一职责原则和 DRY（Don't Repeat Yourself）原则。

## Glossary

- **TaskQueryService**: 统一任务查询服务，负责在三个任务表中搜索任务
- **Repository**: 数据访问层，封装数据库 CRUD 操作
- **TaskType**: 任务类型枚举（MODEL/EDIT/OUTFIT）
- **Guard Clause**: 提前返回策略，用于减少嵌套深度
- **Generic Base Class**: 泛型基类，用于消除重复代码

## Requirements

### Requirement 1: 统一任务状态更新

**User Story:** As a developer, I want a unified task status update mechanism, so that I can avoid duplicating the same three-table lookup logic across multiple services.

#### Acceptance Criteria

1. WHEN a service needs to update task status THEN the TaskQueryService SHALL provide a unified `update_status` method that handles all three task types
2. WHEN the unified update method is called THEN the TaskQueryService SHALL automatically determine the correct repository based on task type
3. WHEN the task is not found THEN the unified update method SHALL return None without throwing an exception
4. WHEN the status update succeeds THEN the unified update method SHALL return the updated TaskQueryResult

### Requirement 2: Repository 泛型基类

**User Story:** As a developer, I want a generic base repository class, so that I can eliminate duplicate CRUD code across the three task repositories.

#### Acceptance Criteria

1. WHEN creating a new task repository THEN the BaseTaskRepository SHALL provide common methods including `get_by_id`, `get_by_task_id`, `update_status`, and `get_pending_tasks`
2. WHEN a repository extends BaseTaskRepository THEN the repository SHALL only need to implement task-specific `create` method
3. WHEN the base repository methods are called THEN the BaseTaskRepository SHALL use the correct model class defined by the subclass
4. WHEN existing repository tests are run THEN all tests SHALL pass without modification

### Requirement 3: 消除 Service 层重复代码

**User Story:** As a developer, I want to remove duplicate three-table lookup code from services, so that the codebase is easier to maintain.

#### Acceptance Criteria

1. WHEN ModelService handles task callbacks THEN the ModelService SHALL use TaskQueryService instead of manual three-table lookup
2. WHEN PollingService handles task events THEN the PollingService SHALL use TaskQueryService instead of manual three-table lookup
3. WHEN TaskService updates task status THEN the TaskService SHALL use the unified update method from TaskQueryService
4. WHEN all services are refactored THEN the existing API behavior SHALL remain unchanged

### Requirement 4: 简化嵌套逻辑

**User Story:** As a developer, I want to reduce nested if-else blocks, so that the code is more readable and maintainable.

#### Acceptance Criteria

1. WHEN TaskPoller extracts error messages THEN the TaskPoller SHALL use a dedicated `_extract_error_message` method
2. WHEN CallbackPayload converts to dict THEN the CallbackPayload SHALL use dictionary comprehension to filter None values
3. WHEN guard clauses can replace nested if-else THEN the code SHALL use early return pattern
4. WHEN refactoring is complete THEN the maximum nesting depth in any function SHALL not exceed 3 levels

### Requirement 5: 保持向后兼容

**User Story:** As a developer, I want the refactoring to be backward compatible, so that existing functionality and tests continue to work.

#### Acceptance Criteria

1. WHEN the refactoring is complete THEN all existing unit tests SHALL pass without modification
2. WHEN the refactoring is complete THEN all existing property-based tests SHALL pass without modification
3. WHEN the API endpoints are called THEN the response format SHALL remain identical to before refactoring
4. WHEN the database operations are performed THEN the data integrity SHALL be maintained
