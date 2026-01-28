# Suitme 变更记录

本文件记录对代码的实际修改（与 `TODO.md` 区分：TODO 是计划，CHANGELOG 是已完成）。

## 2026-01-28

- 新增 `TODO.md`：记录按 Apifox 对齐与稳定性改造的后续事项。
- 轮询修复：`TaskPoller` 按可重试错误重试（429/5xx），不再做本地超时（交由 Apimart 侧超时/失败）（`app/infra/task_poller.py`）。
- 资源治理：避免 `TaskPoller.close()` 迭代时字典被修改导致异常（`app/infra/task_poller.py`）。
- 重启恢复：应用启动后后台扫描 pending 任务并恢复轮询；创建应用级单例 `TaskPoller`/`ApimartClient`（`app/main.py`、`app/services/polling_callbacks.py`）。
- 接口对齐：`GET /tasks/{task_id}` 的 `image` 字段始终返回，并新增 `image_base64` 字段（可为空）（`app/schemas/__init__.py`、`app/services/task_service.py`）。
- Prompt 修复：默认模特 prompt 补上 `body_type` 占位符并修正格式化变量名（`app/prompts.py`）。
- 提交幂等：`apimart_task_id` 仅在为空时绑定；已绑定任务不会重复提交到 Apimart，并对“绑定失败”做重试（`app/repositories/base_task_repository.py`、`app/services/model_service.py`）。
- 启动恢复优化：仅在启动时执行一次恢复，并按 `APIMART_TASK_RETENTION_DAYS` 过滤过期任务（避免 Apimart 返回“任务不存在或已过期”）（`app/config.py`、`app/main.py`）。
- 代码简化：`ModelService` 的提交与写回逻辑抽取为通用方法，并复用 `polling_callbacks`，减少重复代码与不一致风险（`app/services/model_service.py`）。
- 文档快照：保存 Apifox 导出的 `.md` 到 `docs/apifox/` 便于后续对齐。
