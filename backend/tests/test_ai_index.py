"""AI 增量索引测试 — 锁定单篇重建、幂等、归属校验、后台入口与路由接线"""

import asyncio

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.models  # noqa: F401 — 确保全部模型注册到 Base.metadata
from app.core.config import settings
from app.core.database import Base
from app.models.ai import NoteChunk
from app.models.note import Note
from app.models.user import User
from app.services.ai import index_service
from app.services.ai.index_service import IndexService, index_note_in_background
from conftest import register_user


@pytest.fixture()
def no_embedding(monkeypatch):
    """清空密钥强制走降级路径，避免测试触网"""
    monkeypatch.setattr(settings, "AI_API_KEY", "")
    monkeypatch.setattr(settings, "AI_EMBEDDING_API_KEY", "")


def _make_engine(tmp_path):
    """独立临时库引擎；NullPool 保证连接与事件循环同生命周期"""
    return create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'ai_index.db').as_posix()}",
        poolclass=NullPool,
    )


async def _init_db(engine) -> async_sessionmaker[AsyncSession]:
    """建表并返回会话工厂"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _create_user_note(db: AsyncSession, content: str) -> tuple[User, Note]:
    """造一个用户及其笔记"""
    user = User(username="indexer", email="indexer@example.com", password_hash="x")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    note = Note(user_id=user.id, title="前端性能优化", content=content)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return user, note


async def _chunks_of(db: AsyncSession, note_id: int) -> list[NoteChunk]:
    """按序号取回某篇笔记的全部分块"""
    result = await db.execute(
        select(NoteChunk).where(NoteChunk.note_id == note_id).order_by(NoteChunk.chunk_index)
    )
    return list(result.scalars().all())


def test_index_note_writes_chunks_and_replaces_on_rewrite(tmp_path, no_embedding):
    """首次索引写入分块；正文改写后整体替换而不是追加"""

    async def scenario() -> None:
        engine = _make_engine(tmp_path)
        factory = await _init_db(engine)
        async with factory() as db:
            user, note = await _create_user_note(db, "性能优化的要点。" * 400)
            service = IndexService()

            assert await service.index_note(db, user.id, note.id) is True
            first = await _chunks_of(db, note.id)
            assert len(first) > 1
            assert [c.chunk_index for c in first] == list(range(len(first)))
            # 无向量密钥时应降级：分块照常写入，向量留空
            assert all(c.embedding is None for c in first)
            assert all(c.content_hash for c in first)

            note.content = "短内容。" * 50
            db.add(note)
            await db.commit()

            assert await service.index_note(db, user.id, note.id) is True
            second = await _chunks_of(db, note.id)
            assert len(second) < len(first)
            assert [c.chunk_index for c in second] == list(range(len(second)))
        await engine.dispose()

    asyncio.run(scenario())


def test_index_note_is_idempotent(tmp_path, no_embedding):
    """正文不变时重复索引，分块数量与内容哈希保持一致"""

    async def scenario() -> None:
        engine = _make_engine(tmp_path)
        factory = await _init_db(engine)
        async with factory() as db:
            user, note = await _create_user_note(db, "缓存与渲染。" * 200)
            service = IndexService()

            await service.index_note(db, user.id, note.id)
            first = [(c.chunk_index, c.content_hash) for c in await _chunks_of(db, note.id)]

            await service.index_note(db, user.id, note.id)
            second = [(c.chunk_index, c.content_hash) for c in await _chunks_of(db, note.id)]

            assert first == second
        await engine.dispose()

    asyncio.run(scenario())


def test_index_note_rejects_missing_or_foreign_note(tmp_path, no_embedding):
    """不存在的笔记与他人的笔记都不写入分块"""

    async def scenario() -> None:
        engine = _make_engine(tmp_path)
        factory = await _init_db(engine)
        async with factory() as db:
            user, note = await _create_user_note(db, "正文内容。" * 100)
            service = IndexService()

            assert await service.index_note(db, user.id, 999999) is False
            assert await service.index_note(db, user.id + 1, note.id) is False

            total = await db.scalar(select(func.count()).select_from(NoteChunk))
            assert total == 0
        await engine.dispose()

    asyncio.run(scenario())


def test_background_skips_when_ai_not_configured(tmp_path, monkeypatch, no_embedding):
    """未配置模型密钥时后台入口直接返回，不产生分块"""

    async def scenario() -> None:
        engine = _make_engine(tmp_path)
        factory = await _init_db(engine)
        monkeypatch.setattr(index_service, "SessionLocal", factory)
        async with factory() as db:
            user, note = await _create_user_note(db, "正文内容。" * 100)

        assert settings.ai_configured is False
        await index_note_in_background(user.id, note.id)

        async with factory() as db:
            total = await db.scalar(select(func.count()).select_from(NoteChunk))
            assert total == 0
        await engine.dispose()

    asyncio.run(scenario())


def test_background_indexes_note_when_configured(tmp_path, monkeypatch):
    """已配置密钥时后台入口使用独立会话完成索引"""

    async def fake_embed(self, texts):
        """向量服务桩：返回空向量表示降级，避免测试触网"""
        return [[] for _ in texts], False

    async def scenario() -> None:
        engine = _make_engine(tmp_path)
        factory = await _init_db(engine)
        monkeypatch.setattr(settings, "AI_API_KEY", "test-key")
        monkeypatch.setattr(index_service, "SessionLocal", factory)
        monkeypatch.setattr(IndexService, "_embed", fake_embed)

        async with factory() as db:
            user, note = await _create_user_note(db, "正文内容。" * 300)

        assert settings.ai_configured is True
        await index_note_in_background(user.id, note.id)

        async with factory() as db:
            total = await db.scalar(
                select(func.count()).select_from(NoteChunk).where(NoteChunk.note_id == note.id)
            )
            assert total and total > 1
        await engine.dispose()

    asyncio.run(scenario())


def test_note_routes_schedule_incremental_index(client, monkeypatch):
    """创建 / 导入 / 更新笔记都会在响应后触发增量索引"""
    calls: list[tuple[int, int]] = []

    async def fake_index(user_id: int, note_id: int) -> None:
        calls.append((user_id, note_id))

    monkeypatch.setattr("app.routers.notes.index_note_in_background", fake_index)
    auth = register_user(client, "index_router")

    created = client.post(
        "/api/notes", json={"title": "接线验证", "content": "正文"}, headers=auth
    ).json()["data"]
    assert calls and calls[-1][1] == created["id"]

    client.put(f"/api/notes/{created['id']}", json={"content": "改后的正文"}, headers=auth)
    assert len(calls) == 2 and calls[-1][1] == created["id"]

    client.post("/api/notes/import", json={"title": "导入验证", "content": "正文"}, headers=auth)
    assert len(calls) == 3
