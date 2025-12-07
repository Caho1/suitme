# 技术栈

## 核心框架
- **Python 3.12+**
- **FastAPI** - Web 框架
- **Pydantic 2.x** - 数据验证和序列化
- **SQLAlchemy 2.x (async)** - ORM，使用异步模式
- **aiosqlite** - 开发环境数据库（生产使用 MySQL）
- **httpx** - 异步 HTTP 客户端（调用 Apimart API）
- **uvicorn** - ASGI 服务器

## 包管理
- **uv** - Python 包管理器
- 配置文件: `pyproject.toml`
- 锁文件: `uv.lock`

## 测试
- **pytest** + **pytest-asyncio** - 异步测试
- **pytest-httpx** - HTTP mock
- **hypothesis** - 属性测试

## 常用命令

```bash
# 安装依赖
uv sync

# 安装开发依赖
uv sync --extra dev

# 运行服务
uv run uvicorn main:app --reload

# 运行测试
uv run pytest

# 运行单个测试文件
uv run pytest tests/test_xxx.py -v
```

## 外部依赖
- **Apimart Images API** (`api.apimart.ai/v1`) - AI 图像生成
  - `POST /images/generations` - 提交生成任务
  - `GET /tasks/{task_id}` - 查询任务状态

## 每次运行终端都要激活虚拟环境！
- **.venv\Scripts\activate**