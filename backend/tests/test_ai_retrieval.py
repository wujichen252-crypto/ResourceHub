"""检索相关度门槛测试 — 锁定“无依据不硬答”的行为"""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.models  # noqa: F401 — 确保全部模型注册到 Base.metadata
from app.core.database import Base
from app.models.ai import NoteChunk
from app.models.note import Note
from app.models.user import User
from app.services.ai import retrieval
from app.services.ai.retrieval import retrieve


def _make_engine(tmp_path):
    return create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'ai_retrieval.db').as_posix()}",
        poolclass=NullPool,
    )


async def _init_db(engine) -> async_sessionmaker[AsyncSession]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _seed(db: AsyncSession) -> int:
    """一篇相关笔记 + 一篇无关笔记，各一个分块"""
    user = User(username="retriever", email="retriever@example.com", password_hash="x")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    related = Note(user_id=user.id, title="报销流程", content="报销七天内打款")
    unrelated = Note(user_id=user.id, title="团建记录", content="团建去了农场")
    db.add_all([related, unrelated])
    await db.commit()
    await db.refresh(related)
    await db.refresh(unrelated)

    db.add_all(
        [
            NoteChunk(user_id=user.id, note_id=related.id, chunk_index=0, content="报销七天内打款"),
            NoteChunk(user_id=user.id, note_id=unrelated.id, chunk_index=0, content="团建去了农场"),
        ]
    )
    await db.commit()
    return user.id


def test_irrelevant_query_returns_nothing_when_similarity_is_low(tmp_path, monkeypatch):
    """关键词未命中且语义相似度低于门槛时，应判定为无依据"""

    async def scenario() -> None:
        engine = _make_engine(tmp_path)
        factory = await _init_db(engine)
        async with factory() as db:
            user_id = await _seed(db)
            # 两篇都“不太像”：余弦相似度低于门槛，且没有关键词命中
            monkeypatch.setattr(retrieval, "_vector_scores", _fixed_vector([0.2, 0.3]))
            hits = await retrieve(db, user_id, "红烧肉怎么做")
            assert hits == []
        await engine.dispose()

    asyncio.run(scenario())


def test_semantic_match_kept_even_without_keyword_overlap(tmp_path, monkeypatch):
    """同义改写没有字面重合，但语义相似度高时应保留"""

    async def scenario() -> None:
        engine = _make_engine(tmp_path)
        factory = await _init_db(engine)
        async with factory() as db:
            user_id = await _seed(db)
            monkeypatch.setattr(retrieval, "_vector_scores", _fixed_vector([0.66, 0.21]))
            hits = await retrieve(db, user_id, "钱什么时候能到账")
            assert len(hits) == 1
            assert hits[0].note_title == "报销流程"
        await engine.dispose()

    asyncio.run(scenario())


def test_keyword_hit_kept_even_when_vector_unavailable(tmp_path, monkeypatch):
    """向量服务不可用时降级为关键词检索，命中仍应返回"""

    async def scenario() -> None:
        engine = _make_engine(tmp_path)
        factory = await _init_db(engine)
        async with factory() as db:
            user_id = await _seed(db)
            monkeypatch.setattr(retrieval, "_vector_scores", _no_vector())
            hits = await retrieve(db, user_id, "报销多久到账")
            assert len(hits) == 1
            assert hits[0].note_title == "报销流程"
        await engine.dispose()

    asyncio.run(scenario())


def _fixed_vector(values: list[float]):
    """按分块顺序返回固定相似度"""

    async def fake(chunks, query):
        return values[: len(chunks)]

    return fake


def _no_vector():
    """模拟向量服务不可用，触发纯关键词降级"""

    async def fake(chunks, query):
        return None

    return fake


def test_note_without_chunks_is_not_retrievable(tmp_path):
    """笔记还没被 AI 读取（没有分块）时检索必然为空，对应界面上的“重新读取”提示"""

    async def scenario() -> None:
        engine = _make_engine(tmp_path)
        factory = await _init_db(engine)
        async with factory() as db:
            user = User(username="empty", email="empty@example.com", password_hash="x")
            db.add(user)
            await db.commit()
            await db.refresh(user)
            db.add(Note(user_id=user.id, title="未索引笔记", content="报销七天内打款"))
            await db.commit()

            hits = await retrieve(db, user.id, "报销多久到账")
            assert hits == []
        await engine.dispose()

    asyncio.run(scenario())
