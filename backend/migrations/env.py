"""
Alembic 迁移环境 — 适配 SQLAlchemy 2.0 异步引擎

连接串来源：app.core.config.settings.DATABASE_URL（读取 .env / 环境变量，
环境变量优先，因此可在命令行临时覆盖，如基线生成时指向临时 SQLite）。
异步迁移按 CLAUDE-troubleshooting.md 记录的方式：asyncio.run + conn.run_sync。
"""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.database import Base
import app.models  # noqa: F401  — 确保所有模型注册进 Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _connect_args() -> dict:
    """与 app/core/database.py 保持一致的连接参数（MySQL 快速失败）"""
    if settings.DATABASE_URL.startswith("mysql"):
        return {"connect_timeout": 5}
    return {}


def run_migrations_offline() -> None:
    """离线模式：仅生成 SQL 不执行（alembic upgrade --sql）"""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,  # 检测列类型变更
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = create_async_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
        connect_args=_connect_args(),
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
