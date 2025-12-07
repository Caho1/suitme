# Requirements Document

## Introduction

Suitme 数字模特图像生成后端服务是一个基于 FastAPI + MySQL + Apimart Images API 的 Python 服务。该服务负责数字模特形象相关的 AI 生成，包含三个核心功能：生成默认模特、编辑默认模特、穿搭生成。服务只面向 Java 后端，不直接对前端暴露，使用 Apimart 图像生成 API（异步任务模式）进行实际的生图。

## Glossary

- **Suitme**: 数字模特图像生成系统名称
- **默认模特 (Default Model)**: 用户在系统中的标准数字形象，用于后续所有穿搭的基底
- **穿搭生成 (Outfit Generation)**: 将服装单品图"穿"到默认模特形象上，生成穿搭效果图
- **Apimart**: 第三方图像生成 API 服务提供商
- **Base64**: 一种将二进制数据编码为 ASCII 字符串的方法
- **OSS**: 对象存储服务，用于存储生成的图片
- **task_id**: 任务唯一标识符
- **angle**: 视角，包括 front（正面）、side（侧面）、back（背面）
- **body_profile**: 用户身体参数，包含性别、身高、体重、年龄、肤色、身材类型等

## Requirements

### Requirement 1: 默认模特生成 (F1)

**User Story:** As a Java 后端服务, I want to 调用 Python 服务生成用户的默认数字模特形象, so that 用户可以拥有一个标准的数字形象用于后续穿搭展示。

#### Acceptance Criteria

1. WHEN Java 后端提交包含用户正面照片和身体参数的请求 THEN Suitme 服务 SHALL 创建一个生成任务并返回 task_id 和 submitted 状态
2. WHEN 请求中的 user_image_base64 不是有效的 Data URI 格式 THEN Suitme 服务 SHALL 返回 400 状态码和 code=1001 的错误响应
3. WHEN 请求中的 body_profile 字段值超出合理范围 THEN Suitme 服务 SHALL 返回 400 状态码和 code=1001 的错误响应
4. WHEN 任务创建成功 THEN Suitme 服务 SHALL 将任务记录写入 ai_generation_task 表，状态为 submitted
5. WHEN Apimart 任务完成 THEN Suitme 服务 SHALL 下载图片并存储为 Base64 或上传至 OSS，然后写入 ai_generation_image 表

### Requirement 2: 默认模特编辑 (F2)

**User Story:** As a Java 后端服务, I want to 调用 Python 服务编辑已有的默认模特形象, so that 用户可以调整数字形象的部分特征（如发型、身材等）。

#### Acceptance Criteria

1. WHEN Java 后端提交包含 base_model_task_id 和编辑指令的请求 THEN Suitme 服务 SHALL 创建一个编辑任务并返回 task_id 和 submitted 状态
2. WHEN base_model_task_id 对应的基础模特图不存在 THEN Suitme 服务 SHALL 返回 400 或 404 状态码的错误响应
3. WHEN 编辑任务创建成功 THEN Suitme 服务 SHALL 将任务记录写入 ai_generation_task 表，type 为 edit，并关联 base_model_task_id
4. WHEN 编辑任务完成 THEN Suitme 服务 SHALL 生成保持人物身份一致的新模特图

### Requirement 3: 穿搭生成 (F3)

**User Story:** As a Java 后端服务, I want to 调用 Python 服务生成模特穿搭效果图, so that 用户可以预览服装穿在数字模特身上的效果。

#### Acceptance Criteria

1. WHEN Java 后端提交包含 base_model_task_id、angle 和服装图的请求 THEN Suitme 服务 SHALL 创建一个穿搭生成任务并返回 task_id、status 和 angle
2. WHEN angle 参数不在 front/side/back 枚举中 THEN Suitme 服务 SHALL 返回 400 状态码的错误响应
3. WHEN base_model_task_id 对应的基础模特图不存在 THEN Suitme 服务 SHALL 返回 400 或 404 状态码的错误响应
4. WHEN 穿搭任务创建成功 THEN Suitme 服务 SHALL 将任务记录写入 ai_generation_task 表，type 为 outfit，并记录 angle 字段

### Requirement 4: 异步任务管理

**User Story:** As a 系统管理员, I want to Suitme 服务能够管理所有异步生图任务的状态, so that 任务可以被正确跟踪和处理。

#### Acceptance Criteria

1. WHEN 任务提交到 Apimart THEN Suitme 服务 SHALL 将任务状态设置为 submitted 并开始后台轮询
2. WHEN 轮询 Apimart 返回处理中状态 THEN Suitme 服务 SHALL 更新任务状态为 processing 并记录进度
3. WHEN 轮询 Apimart 返回完成状态 THEN Suitme 服务 SHALL 下载图片、存储、更新任务状态为 completed，并触发回调通知 Java
4. WHEN 轮询 Apimart 返回失败状态 THEN Suitme 服务 SHALL 更新任务状态为 failed，记录错误信息，并触发回调通知 Java
5. WHEN 任务轮询超过配置的超时时间（如 120 秒） THEN Suitme 服务 SHALL 标记任务为 failed，error_message 为 timeout

### Requirement 5: 任务状态查询

**User Story:** As a Java 后端服务, I want to 查询任务的当前状态和结果, so that 可以获取生成的图片或了解任务进度。

#### Acceptance Criteria

1. WHEN Java 后端查询存在的 task_id THEN Suitme 服务 SHALL 返回任务的当前状态、进度和（如已完成）图片信息
2. WHEN Java 后端查询不存在的 task_id THEN Suitme 服务 SHALL 返回 404 状态码和 code=1003 的错误响应
3. WHEN 任务状态为 completed THEN Suitme 服务 SHALL 在响应中包含图片的 Base64 或 OSS URL

### Requirement 6: 错误处理

**User Story:** As a 系统管理员, I want to Suitme 服务能够正确处理各种错误情况, so that 系统可以稳定运行并提供有意义的错误信息。

#### Acceptance Criteria

1. WHEN Apimart 返回 400 参数错误 THEN Suitme 服务 SHALL 标记任务为 failed，code=1002
2. WHEN Apimart 返回 401 鉴权错误 THEN Suitme 服务 SHALL 标记任务为 failed 并触发报警
3. WHEN Apimart 返回 402 余额不足 THEN Suitme 服务 SHALL 标记任务为 failed 并触发报警
4. WHEN Apimart 返回 429 频率限制 THEN Suitme 服务 SHALL 进行短时间重试，仍失败则标记任务为 failed
5. WHEN Apimart 返回 5xx 错误 THEN Suitme 服务 SHALL 按指数退避策略重试，仍失败则标记任务为 failed

### Requirement 7: Java 后端回调

**User Story:** As a Java 后端服务, I want to 接收 Python 服务的任务完成回调, so that 可以及时更新业务数据并通知前端。

#### Acceptance Criteria

1. WHEN 任务完成或失败 THEN Suitme 服务 SHALL 调用 Java 的回调接口，传递 task_id、status、type、angle 和图片信息
2. WHEN 回调失败 THEN Suitme 服务 SHALL 进行重试
3. WHEN 发送回调请求 THEN Suitme 服务 SHALL 在请求头中包含共享 token 用于身份验证

### Requirement 8: 数据持久化

**User Story:** As a 系统管理员, I want to 所有任务和图片数据被正确持久化到数据库, so that 数据可以被查询和追溯。

#### Acceptance Criteria

1. WHEN 创建任务 THEN Suitme 服务 SHALL 在 ai_generation_task 表中插入记录，包含 request_id、external_task_id、type、user_id、status 等字段
2. WHEN 任务完成 THEN Suitme 服务 SHALL 在 ai_generation_image 表中插入记录，包含 task_id、angle、image_base64 或 image_url
3. WHEN 更新任务状态 THEN Suitme 服务 SHALL 同时更新 updated_at 字段
4. WHEN 任务完成 THEN Suitme 服务 SHALL 设置 completed_at 字段
