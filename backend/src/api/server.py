"""
FastAPI 服务入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from src.api.routes import router
from src.config.settings import settings
from src.db.database import init_db, close_db
from src.pipeline.batch_processor import recover_unfinished


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期事件"""
    # 启动时初始化数据库
    await init_db()
    # 恢复未完成的批改任务
    await recover_unfinished()
    print(f"\n{'='*50}")
    print(f"  {settings.PROJECT_NAME} v{settings.VERSION}")
    print(f"  API: http://{settings.API_HOST}:{settings.API_PORT}")
    print(f"  Docs: http://{settings.API_HOST}:{settings.API_PORT}/docs")
    print(f"{'='*50}\n")
    yield
    # 关闭时释放连接池
    await close_db()
    print("\n  Shutting down...\n")


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="儿童英文作文 AI 批改系统",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api/v1")

    return app


app = create_app()
