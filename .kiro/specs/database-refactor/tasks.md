# 实现计划

- [x] 1. 创建新数据库模型





  - [x] 1.1 创建 BaseModelTask 模型


    - 在 app/models/__init__.py 中定义 `base_model_task` 表
    - 包含 body_profile 字段（gender, height_cm, weight_kg, age, skin_tone, body_shape）
    - 添加 status, progress, timestamps 字段
    - _需求: 1.1, 2.1_

  - [x] 1.2 创建 EditTask 模型
    - 定义 `edit_task` 表，包含 base_model_id 外键
    - 添加 edit_instructions 字段
    - _需求: 1.2, 2.2, 4.1_

  - [x] 1.3 创建 OutfitTask 模型
    - 定义 `outfit_task` 表，包含 base_model_id 外键
    - 添加 angle, outfit_description 字段
    - _需求: 1.3, 2.3, 4.2_
  - [x] 1.4 更新 GenerationImage 模型

    - 重命名表为 `generation_image`
    - 添加 task_type 字段用于多态关联
    - _需求: 1.4, 2.4_

  - [x] 1.5 删除旧的 AIGenerationTask 模型
    - 移除旧的统一任务模型
    - _需求: 1.1_

- [x] 2. 创建新的 Repository





  - [x] 2.1 创建 BaseModelTaskRepository


    - 实现 create, get_by_id, get_by_task_id, update_status 方法
    - _需求: 3.1_
  - [x] 2.2 创建 EditTaskRepository


    - 实现 create, get_by_id, get_by_task_id, update_status 方法
    - 添加 base_model_id 验证
    - _需求: 3.2_

  - [x] 2.3 创建 OutfitTaskRepository

    - 实现 create, get_by_id, get_by_task_id, update_status 方法
    - 添加 base_model_id 验证
    - _需求: 3.3_

  - [x] 2.4 更新 ImageRepository

    - 更新为使用 task_type 进行多态查询
    - _需求: 2.4_

  - [x] 2.5 删除旧的 TaskRepository

    - 移除旧的统一 Repository
    - _需求: 1.1_

- [x] 3. 更新 Service 层





  - [x] 3.1 更新 ModelService.create_default_model


    - 使用 BaseModelTaskRepository
    - 将 body_profile 字段存储到任务记录
    - _需求: 2.1, 3.1_

  - [x] 3.2 更新 ModelService.edit_model
    - 使用 EditTaskRepository
    - 验证 base_model_id 存在
    - _需求: 2.2, 3.2_
  - [x] 3.3 更新 ModelService.create_outfit

    - 使用 OutfitTaskRepository
    - 验证 base_model_id 存在
    - _需求: 2.3, 3.3_

  - [x] 3.4 更新任务完成处理器
    - 更新 _handle_task_completed 根据任务类型使用正确的 Repository
    - _需求: 2.4_

- [x] 4. 更新任务状态查询







  - [x] 4.1 创建 TaskQueryService


    - 实现统一的任务查询，搜索所有三个表
    - 返回一致的响应格式
    - _需求: 3.4_

  - [x] 4.2 更新 TaskService.get_task_status





    - 使用 TaskQueryService 在任意表中查找任务
    - _需求: 3.4_

- [x] 5. 检查点 - 确保所有测试通过






  - 确保所有测试通过，如有问题询问用户

- [ ] 6. 数据库迁移
  - [ ] 6.1 创建迁移脚本
    - 删除旧表
    - 创建新表
    - _需求: 1.1, 1.2, 1.3, 1.4_

- [ ]* 7. 属性测试
  - [ ]* 7.1 编写任务类型隔离的属性测试
    - **属性 1: 任务类型隔离**
    - **验证: 需求 1.1, 1.2, 1.3**
  - [ ]* 7.2 编写外键完整性的属性测试
    - **属性 2: 外键完整性**
    - **验证: 需求 4.1, 4.2**
  - [ ]* 7.3 编写任务查询一致性的属性测试
    - **属性 3: 任务查询一致性**
    - **验证: 需求 3.4**
  - [ ]* 7.4 编写图片关联的属性测试
    - **属性 4: 图片关联**
    - **验证: 需求 2.4**

- [ ] 8. 最终检查点 - 确保所有测试通过
  - 确保所有测试通过，如有问题询问用户
