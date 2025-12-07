# Implementation Plan

- [x] 1. 项目基础设施搭建





  - [x] 1.1 配置项目依赖和目录结构





    - 在 pyproject.toml 添加依赖：fastapi, uvicorn, sqlalchemy, httpx, pydantic, hypothesis, pytest, pytest-asyncio
    - 创建目录结构：app/routes, app/services, app/repositories, app/infra, app/models, app/schemas, tests
    - _Requirements: 8.1_
  - [x] 1.2 配置数据库连接和 SQLAlchemy


    - 创建 app/database.py 配置异步数据库连接
    - 配置 alembic 或手动创建表
    - _Requirements: 8.1_

  - [x] 1.3 创建配置管理模块

    - 创建 app/config.py 管理环境变量（数据库 URL、Apimart API Key、回调 URL、超时配置等）
    - _Requirements: 4.5, 6.1-6.5_

- [x] 2. 数据模型实现






  - [x] 2.1 创建 Pydantic 请求/响应模型

    - 实现 BodyProfile、DefaultModelRequest、EditModelRequest、OutfitModelRequest
    - 实现 TaskResponse、TaskData、ErrorResponse
    - _Requirements: 1.1, 2.1, 3.1_


  - [x] 2.2 编写属性测试：无效 Base64 输入拒绝

    - **Property 2: 无效 Base64 输入拒绝**
    - **Validates: Requirements 1.2**
  - [x] 2.3 编写属性测试：无效 body_profile 参数拒绝

    - **Property 3: 无效 body_profile 参数拒绝**
    - **Validates: Requirements 1.3**
  - [x] 2.4 编写属性测试：无效 angle 参数拒绝


    - **Property 5: 无效 angle 参数拒绝**
    - **Validates: Requirements 3.2**
  - [x] 2.5 创建 SQLAlchemy 数据库模型


    - 实现 AIGenerationTask 模型（含枚举 TaskType、TaskStatus）
    - 实现 AIGenerationImage 模型
    - _Requirements: 8.1, 8.2_

- [x] 3. Repository 层实现





  - [x] 3.1 实现 TaskRepository


    - 实现 create、get_by_id、update_status、get_pending_tasks 方法
    - _Requirements: 8.1, 8.3, 8.4_
  - [x] 3.2 实现 ImageRepository


    - 实现 create、get_by_task_id 方法
    - _Requirements: 8.2_
  - [x] 3.3 编写属性测试：任务创建数据持久化


    - **Property 6: 任务创建数据持久化**
    - **Validates: Requirements 1.4, 2.3, 3.4, 8.1**
  - [x] 3.4 编写属性测试：任务时间戳正确更新


    - **Property 12: 任务时间戳正确更新**
    - **Validates: Requirements 8.3, 8.4**

- [x] 4. Checkpoint - 确保所有测试通过





  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Apimart 客户端实现





  - [x] 5.1 实现 ApimartClient


    - 实现 submit_generation 方法（POST /v1/images/generations）
    - 实现 get_task_status 方法（GET /v1/tasks/{task_id}）
    - _Requirements: 4.1_
  - [x] 5.2 实现错误处理和重试逻辑


    - 实现 ApimartErrorHandler 处理 400/401/402/429/5xx 错误
    - 实现指数退避重试策略
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 6. Service 层实现





  - [x] 6.1 实现 ModelService - 默认模特生成


    - 实现 create_default_model 方法
    - 构建 Prompt 模板
    - _Requirements: 1.1, 1.4_
  - [x] 6.2 实现 ModelService - 模特编辑


    - 实现 edit_model 方法
    - 验证 base_model_task_id 存在
    - _Requirements: 2.1, 2.2, 2.3_
  - [x] 6.3 实现 ModelService - 穿搭生成


    - 实现 create_outfit 方法
    - 验证 angle 和 base_model_task_id
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  - [x] 6.4 编写属性测试：无效 base_model_task_id 拒绝


    - **Property 4: 无效 base_model_task_id 拒绝**
    - **Validates: Requirements 2.2, 3.3**
  - [x] 6.5 实现 TaskService


    - 实现 get_task_status、update_task_status、complete_task、fail_task 方法
    - _Requirements: 5.1, 5.2, 5.3, 4.2, 4.3, 4.4_
  - [x] 6.6 编写属性测试：任务状态转换正确性


    - **Property 7: 任务状态转换正确性**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**

- [x] 7. Checkpoint - 确保所有测试通过





  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. API 路由实现





  - [x] 8.1 实现 /models/default 路由


    - 参数校验、调用 ModelService、返回 202 响应
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 8.2 实现 /models/edit 路由

    - 参数校验、调用 ModelService、返回 202 响应
    - _Requirements: 2.1, 2.2_

  - [x] 8.3 实现 /models/outfit 路由

    - 参数校验、调用 ModelService、返回 202 响应
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 8.4 实现 /tasks/{task_id} 路由

    - 查询任务状态、返回图片信息
    - _Requirements: 5.1, 5.2, 5.3_
  - [x] 8.5 编写属性测试：任务创建返回正确响应


    - **Property 1: 任务创建返回正确响应**
    - **Validates: Requirements 1.1, 2.1, 3.1**
  - [x] 8.6 编写属性测试：任务查询返回正确信息


    - **Property 8: 任务查询返回正确信息**
    - **Validates: Requirements 5.1, 5.3**
  - [x] 8.7 编写属性测试：不存在任务查询返回 404


    - **Property 9: 不存在任务查询返回 404**
    - **Validates: Requirements 5.2**

- [x] 9. 异步任务轮询实现





  - [x] 9.1 实现 TaskPoller


    - 实现 start_polling 和 poll_loop 方法
    - 配置轮询间隔和超时时间
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
  - [x] 9.2 实现任务完成处理


    - 下载图片、存储 Base64/上传 OSS、写入 ai_generation_image 表
    - _Requirements: 1.5, 8.2_
  - [x] 9.3 编写属性测试：任务完成图片持久化


    - **Property 10: 任务完成图片持久化**
    - **Validates: Requirements 1.5, 8.2**

- [x] 10. 回调处理实现






  - [x] 10.1 实现 CallbackHandler

    - 实现 notify_java 方法
    - 添加身份验证 token 到请求头
    - 实现重试逻辑
    - _Requirements: 7.1, 7.2, 7.3_
  - [x] 10.2 编写属性测试：回调包含正确信息


    - **Property 11: 回调包含正确信息**
    - **Validates: Requirements 7.1, 7.3**

- [x] 11. 应用入口和启动配置






  - [x] 11.1 创建 FastAPI 应用入口

    - 创建 app/main.py 注册路由、配置中间件
    - 配置启动时初始化数据库连接
    - _Requirements: 1.1, 2.1, 3.1, 5.1_

  - [x] 11.2 创建启动脚本

    - 配置 uvicorn 启动参数
    - _Requirements: 1.1_

- [x] 12. Final Checkpoint - 确保所有测试通过





  - Ensure all tests pass, ask the user if questions arise.
