# Suitme TODO

> 以 Apifox 最终文档为准（字段/结构优先）。本文件用于记录需要逐步完善的事项。

## P0（线上稳定性）

- [x] 修复轮询对 Apimart 错误的判定逻辑（429/5xx 应重试，401/402/400 应失败）。
- [x] 轮询不做本地超时（交由 Apimart 侧超时/失败）。
- [x] 服务重启后恢复轮询：扫描数据库 `submitted/processing` 且已绑定 `apimart_task_id` 的任务，重新启动轮询。
- [x] 启动恢复轮询增加过期过滤：超过 `APIMART_TASK_RETENTION_DAYS` 的 pending 任务直接标记失败，不再请求 Apimart。
- [x] 轮询/OSS/HTTP 客户端资源统一管理：避免每个请求创建一个 `TaskPoller/OSSClient` 导致连接泄漏。
- [x] 提交阶段幂等保护：已绑定 `apimart_task_id` 的任务不会重复提交到 Apimart，且不会覆盖已绑定的 `apimart_task_id`。

## P1（对外接口一致性）

- [x] 对齐 Apifox 文档：`GET /tasks/{task_id}` 返回 `image.image_base64` 字段（可为空），并确保字段始终存在。
- [ ] 明确 `task_id` 的类型：Apifox 导出里有 `integer`，但示例/现有实现是 `task_xxx` 字符串；需要统一并更新文档与实现。
- [ ] 明确 `body_profile` 的必填性：Apifox required 未包含 `body_profile`，但业务上生成默认模特通常需要；需要统一。
- [ ] 统一 `type` 枚举值：当前为 `model/edit/outfit`，部分旧文档写的是 `default/edit/outfit`；需要统一并兼容历史。

## P2（回调与可观测性）

- [ ] 串起来 `CallbackHandler`：任务完成/失败时通知 Java 后端（带鉴权 Token、重试、幂等）。
- [ ] 增加结构化日志：记录 `task_id/apimart_task_id/user_id`，便于排障与追踪。
- [ ] 增加指标/健康：活跃轮询数量、超时数量、失败原因分布。

## P3（安全与治理）

- [ ] 生产环境限制 CORS Origins（不要 `*`）。
- [ ] 500 错误不要回显内部异常详情（避免泄漏敏感信息）。
- [ ] `user_id` 权限校验：禁止用别人的 `base_model_task_id` 创建 edit/outfit 或查询任务。

## P4（测试与文档）

- [ ] 清理/更新 `tests/`：当前大量用例与字段已不一致（历史遗留），需要按 Apifox 最终文档重写或拆分为单元测试。
- [ ] 更新仓库内 `API_DOC.md` 与 Apifox 保持一致，避免“两个真相源”。
