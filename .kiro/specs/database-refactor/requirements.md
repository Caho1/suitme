# Requirements Document

## Introduction

重构数据库表结构，将当前单一的 `ai_generation_task` 表拆分为多个独立的任务表，以提高数据模型的清晰度和可维护性。每种任务类型（模特生成、模特编辑、穿搭生成）将有独立的表结构，便于管理和查询。

## Glossary

- **ModelTask**: 模特生成任务，根据用户照片和身体参数生成数字模特
- **EditTask**: 模特编辑任务，在已有模特基础上进行局部调整
- **OutfitTask**: 穿搭生成任务，将服装穿到数字模特上
- **TaskStatus**: 任务状态枚举（submitted, processing, completed, failed）
- **task_id**: Apimart 返回的任务标识符

## Requirements

### Requirement 1

**User Story:** As a developer, I want separate database tables for each task type, so that the data model is clearer and easier to maintain.

#### Acceptance Criteria

1. THE system SHALL store model generation tasks in a dedicated `ai_model_task` table
2. THE system SHALL store edit tasks in a dedicated `ai_edit_task` table with a foreign key reference to `ai_model_task`
3. THE system SHALL store outfit tasks in a dedicated `ai_outfit_task` table with a foreign key reference to `ai_model_task`
4. THE system SHALL store generated images in `ai_generation_image` table with polymorphic references to task tables

### Requirement 2

**User Story:** As a developer, I want each task table to have appropriate fields for its specific use case, so that data is stored efficiently.

#### Acceptance Criteria

1. WHEN a model task is created THEN the system SHALL store user_id, request_id, task_id, body_profile fields, status, and timestamps
2. WHEN an edit task is created THEN the system SHALL store user_id, request_id, task_id, base_model_id, edit_instructions, status, and timestamps
3. WHEN an outfit task is created THEN the system SHALL store user_id, request_id, task_id, base_model_id, angle, outfit_description, status, and timestamps
4. WHEN a task is completed THEN the system SHALL store the generated image with reference to the specific task

### Requirement 3

**User Story:** As a developer, I want the API to continue working with the new table structure, so that existing functionality is preserved.

#### Acceptance Criteria

1. WHEN creating a model task THEN the system SHALL insert into `ai_model_task` and return the task_id
2. WHEN creating an edit task THEN the system SHALL validate the base_model_id exists and insert into `ai_edit_task`
3. WHEN creating an outfit task THEN the system SHALL validate the base_model_id exists and insert into `ai_outfit_task`
4. WHEN querying task status THEN the system SHALL look up the task in the appropriate table based on task_id prefix or type

### Requirement 4

**User Story:** As a developer, I want proper relationships between tables, so that data integrity is maintained.

#### Acceptance Criteria

1. THE system SHALL enforce foreign key constraints between edit_task and model_task
2. THE system SHALL enforce foreign key constraints between outfit_task and model_task
3. WHEN a model task is deleted THEN the system SHALL handle related edit and outfit tasks appropriately
4. THE system SHALL use cascade delete for images when their parent task is deleted
