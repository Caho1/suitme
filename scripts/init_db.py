"""
数据库初始化脚本

创建所有数据库表。
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.database import init_db, create_all_tables, close_db
from app.models import AIGenerationTask, AIGenerationImage  # noqa: F401


async def main():
    """初始化数据库"""
    settings = get_settings()
    print(f"连接数据库: {settings.database_url}")
    
    init_db(settings.database_url, echo=True)
    
    print("创建数据库表...")
    await create_all_tables()
    
    print("数据库初始化完成！")
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
