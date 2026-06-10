"""
应用入口
启动: python -m src.app  (在 backend/ 目录下)
"""
import asyncio
import uvicorn
from src.api.server import app
from src.config.settings import settings
from src.db.database import init_db


async def on_startup():
    """启动时初始化数据库连接"""
    await init_db()


if __name__ == "__main__":
    # 先在当前事件循环中初始化数据库
    asyncio.run(init_db())

    uvicorn.run(
        "src.api.server:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )
