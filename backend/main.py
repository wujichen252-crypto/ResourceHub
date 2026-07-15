"""
ResourceHub Backend — FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.routers import auth, notes, prompts, categories

app = FastAPI(
    title="ResourceHub API",
    description="个人知识管理与 AI 提示词管理的一体化工具",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    redirect_slashes=False,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(notes.router, prefix="/api/notes", tags=["笔记"])
app.include_router(prompts.router, prefix="/api/prompts", tags=["提示词"])
app.include_router(categories.router, prefix="/api/categories", tags=["分类"])


@app.on_event("startup")
async def startup():
    """启动时创建数据库表（开发环境）"""
    async with engine.begin() as conn:
        from app.models import user, note, prompt, category  # noqa
        await conn.run_sync(Base.metadata.create_all)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
