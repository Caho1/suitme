# 实现计划

- [x] 1. 创建 BaseTaskRepository 泛型基类





  - [x] 1.1 创建 `app/repositories/base_task_repository.py` 泛型基类


    - 定义 `BaseTaskRepository[T]`，包含 `model: Type[T]` 类属性
    - 实现 `get_by_id`、`get_by_task_id`、`update_status`、`get_pending_tasks` 方法
    - _需求: 2.1, 2.3_
  - [ ]* 1.2 编写基类方法的属性测试
    - **Property 2: Base repository methods work for all subclasses**
    - **Validates: Requirements 2.1, 2.3**
  - [x] 1.3 重构 BaseModelTaskRepository 继承泛型基类


    - 删除重复方法，只保留 `create` 方法
    - 设置 `model = BaseModelTask`
    - _需求: 2.2_
  - [x] 1.4 重构 EditTaskRepository 继承泛型基类


    - 删除重复方法，只保留 `create` 和 `_validate_base_model_exists`
    - 设置 `model = EditTask`
    - _需求: 2.2_
  - [x] 1.5 重构 OutfitTaskRepository 继承泛型基类


    - 删除重复方法，只保留 `create` 和 `_validate_base_model_exists`
    - 设置 `model = OutfitTask`


    - _需求: 2.2_
  - [x] 1.6 更新 `app/repositories/__init__.py` 导出 BaseTaskRepository

    - _需求: 2.1_


- [x] 2. 检查点 - 确保 Repository 重构正常





  - 运行所有测试，如有问题询问用户

- [x] 3. 扩展 TaskQueryService 添加统一更新方法





  - [x] 3.1 添加 `_get_repo_by_type` 方法


    - 根据 TaskType 返回对应的 repository
    - _需求: 1.2_
  - [x] 3.2 添加 `update_status` 统一更新方法


    - 查找任务、确定类型、调用对应 repository 的 update_status
    - 任务不存在时返回 None
    - _需求: 1.1, 1.3, 1.4_
  - [ ]* 3.3 编写统一更新路由的属性测试
    - **Property 1: Unified update routes to correct repository**
    - **Validates: Requirements 1.1, 1.2, 1.4**

- [x] 4. 重构 Services 使用 TaskQueryService





  - [x] 4.1 重构 ModelService 回调处理器


    - 用 TaskQueryService 替换 `_handle_task_progress` 中的三表查询
    - 用 TaskQueryService 替换 `_handle_task_completed` 中的三表查询
    - 用 TaskQueryService 替换 `_handle_task_failed` 中的三表查询
    - _需求: 3.1_
  - [x] 4.2 重构 PollingService 回调处理器


    - 用 TaskQueryService.find_by_task_id 替换 `_find_task_by_task_id`
    - 在 `_handle_task_progress` 中使用 TaskQueryService.update_status
    - 在 `_handle_task_completed` 中使用 TaskQueryService.update_status
    - 在 `_handle_task_failed` 中使用 TaskQueryService.update_status
    - _需求: 3.2_
  - [x] 4.3 简化 TaskService 使用 TaskQueryService


    - 在 `update_task_status` 中使用 TaskQueryService.update_status
    - 在 `complete_task` 中使用 TaskQueryService.update_status
    - 在 `fail_task` 中使用 TaskQueryService.update_status
    - _需求: 3.3_

- [ ] 5. 检查点 - 确保 Service 重构正常
  - 运行所有测试，如有问题询问用户

- [x] 6. 简化嵌套逻辑





  - [x] 6.1 在 TaskPoller 中添加 `_extract_error_message` 静态方法


    - 处理 string、dict（有/无 "message" 键）、None 等情况
    - _需求: 4.1_
  - [ ]* 6.2 编写错误消息提取的属性测试
    - **Property 3: Error message extraction handles all formats**
    - **Validates: Requirements 4.1**
  - [x] 6.3 重构 `_poll_loop` 使用 `_extract_error_message`


    - 用方法调用替换内联的错误解析逻辑
    - _需求: 4.1_
  - [x] 6.4 使用字典推导式简化 CallbackPayload.to_dict


    - 用字典推导式替换多个 if 语句
    - _需求: 4.2_
  - [ ]* 6.5 编写 CallbackPayload.to_dict 的属性测试
    - **Property 4: CallbackPayload to_dict filters None values**
    - **Validates: Requirements 4.2**

- [x] 7. 验证向后兼容性





  - [x] 7.1 编写 API 响应格式的属性测试








    - **Property 5: API response format unchanged**
    - **Validates: Requirements 3.4, 5.3**
  - [x]* 7.2 编写数据库完整性的属性测试


    - **Property 6: Database operations maintain data integrity**
    - **Validates: Requirements 5.4**

- [ ] 8. 最终检查点 - 运行所有测试




  - 运行所有测试，如有问题询问用户
