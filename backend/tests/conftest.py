"""
pytest 测试基建
- 每个用例独立临时 SQLite 文件库，不依赖远端 MySQL、不依赖已启动的服务
- 不使用 `with TestClient(app)`：避免触发 startup 建表事件（会连接配置中的真实数据库）
"""
import asyncio
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

# 必须在导入应用前设置：占位连接串 + 关闭 SQL echo（真实连接由下方 get_db 覆盖提供）
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./_pytest_placeholder.db"
os.environ["DEBUG"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.models  # noqa: F401 — 确保全部模型注册到 Base.metadata
from app.core.database import Base
from app.core.deps import get_db
from main import app as fastapi_app


@pytest.fixture()
def client(tmp_path):
    """独立数据库的 TestClient；NullPool 保证连接在请求自身的事件循环内创建与释放"""
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}",
        poolclass=NullPool,
    )

    async def _create_tables() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_create_tables())

    TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db():
        async with TestSessionLocal() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = _override_get_db

    yield TestClient(fastapi_app)

    fastapi_app.dependency_overrides.clear()

    async def _dispose() -> None:
        await engine.dispose()

    asyncio.run(_dispose())


def register_user(client: TestClient, username: str, password: str = "password123") -> dict:
    """注册用户并返回带 JWT 的请求头"""
    client.post(
        "/api/auth/register",
        json={"username": username, "password": password, "email": f"{username}@example.com"},
    )
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def auth(client):
    """默认已登录用户 alice 的认证头"""
    return register_user(client, "alice")
