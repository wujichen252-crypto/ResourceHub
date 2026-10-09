"""
数据库连接与会话管理
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

database_connect_args = {}
# 池参数仅对 MySQL 生效：SQLite 的 NullPool 不接受 pool_timeout/pool_recycle
engine_kwargs = {}
if settings.DATABASE_URL.startswith("mysql"):
    # 远端数据库不可达时在 5 秒内失败，避免启动和登录请求长期挂起。
    database_connect_args = {"connect_timeout": 5}
    engine_kwargs = {"pool_timeout": 5, "pool_recycle": 1800}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=database_connect_args,
    **engine_kwargs,
)

SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入 — 获取数据库会话"""
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
