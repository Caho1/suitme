# 项目结构

```
suitme/
├── main.py              # 应用入口
├── pyproject.toml       # 项目配置和依赖
├── app/
│   ├── routes/          # API 路由层 - FastAPI 路由定义
│   ├── schemas/         # Pydantic 模型 - 请求/响应数据结构
│   ├── services/        # 业务逻辑层 - 核心业务处理
│   ├── repositories/    # 数据访问层 - 数据库操作
│   ├── models/          # SQLAlchemy 模型 - 数据库表定义
│   └── infra/           # 基础设施 - Apimart 客户端、任务轮询、回调处理
└── tests/               # 测试目录
```

## 分层架构

采用分层架构，依赖方向：`routes → services → repositories → models`

- **routes**: 接收请求，参数校验，调用 service，返回响应
- **schemas**: 定义 API 的请求体和响应体结构
- **services**: 业务逻辑编排，调用 repository 和 infra
- **repositories**: 数据库 CRUD 操作封装
- **models**: SQLAlchemy ORM 模型定义
- **infra**: 外部服务集成（Apimart API、任务轮询机制）

## 数据库表

- `ai_generation_task` - 生图任务记录
- `ai_generation_image` - 生成图片存储
