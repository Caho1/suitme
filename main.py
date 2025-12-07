"""
Suitme 数字模特图像生成服务启动脚本

使用 uvicorn 启动 FastAPI 应用。
"""

import uvicorn

from app.config import get_settings


def main() -> None:
    """
    启动应用
    
    配置 uvicorn 启动参数并运行服务。
    """
    settings = get_settings()
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发环境启用热重载
        log_level="info",
    )


if __name__ == "__main__":
    main()
