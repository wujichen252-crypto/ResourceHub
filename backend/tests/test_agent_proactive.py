"""主动性测试 — 每日回顾、目标提醒去重、已读与未读计数"""

import asyncio
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.models  # noqa: F401 — 确保全部模型注册到 Base.metadata
from app.core.config import settings
from app.core.database import Base
from app.models.agent import AgentMemory, AgentProactiveMessage
from app.models.note import Note
from app.models.user import User
from app.services.ai.proactive_service import ProactiveService
from conftest import register_user


def _create_note(client, auth, title: str = "Vue 3 响应式原理") -> int:
    response = client.post(
        "/api/notes",
        json={"title": title, "content": "# 笔记\n今天复习了 effect 依赖收集。", "tags": []},
        headers=auth,
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


def test_scan_creates_review_and_read(client, auth, monkeypatch):
    """手动扫描生成今日回顾，可标记已读，未读计数同步"""
    monkeypatch.setattr(settings, "AI_API_KEY", "")
    monkeypatch.setattr(settings, "AI_EMBEDDING_API_KEY", "")
    _create_note(client, auth)

    scan = client.post("/api/ai/proactive/scan", headers=auth)
    assert scan.status_code == 200
    assert scan.json()["data"]["created"] == 1

    messages = client.get("/api/ai/proactive/messages", headers=auth).json()["data"][
        "items"
    ]
    assert len(messages) == 1
    assert messages[0]["kind"] == "daily_review"
    assert messages[0]["status"] == "unread"

    status = client.get("/api/ai/status", headers=auth).json()["data"]
    assert status["unread_proactive_count"] == 1

    read = client.put(
        f"/api/ai/proactive/messages/{messages[0]['id']}/read", headers=auth
    )
    assert read.json()["data"]["status"] == "read"
    status = client.get("/api/ai/status", headers=auth).json()["data"]
    assert status["unread_proactive_count"] == 0

    again = client.post("/api/ai/proactive/scan", headers=auth)
    assert again.json()["data"]["created"] == 0


def test_daily_review_skips_without_notes(client, auth, monkeypatch):
    """没有笔记和目标时不生成空回顾"""
    monkeypatch.setattr(settings, "AI_API_KEY", "")
    scan = client.post("/api/ai/proactive/scan", headers=auth)
    assert scan.json()["data"]["created"] == 0
    messages = client.get("/api/ai/proactive/messages", headers=auth).json()["data"][
        "items"
    ]
    assert messages == []


def test_stale_goal_dedup(tmp_path, monkeypatch):
    """长期目标提醒在冷却期内不重复"""

    async def scenario() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'proactive.db').as_posix()}",
            poolclass=NullPool,
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        async with session_factory() as db:
            user = User(username="proactive", email="p@example.com", password_hash="x")
            db.add(user)
            await db.commit()
            await db.refresh(user)
            db.add(Note(user_id=user.id, title="学习记录", content="正文"))
            db.add(
                AgentMemory(
                    user_id=user.id,
                    memory_type="goal",
                    content="学会 Vue 3",
                    importance=5,
                    source="manual",
                    created_at=datetime.now() - timedelta(days=40),
                )
            )
            await db.commit()

            service = ProactiveService()
            first = await service.scan_stale_goals(db, user.id)
            assert first.created == 1
            second = await service.scan_stale_goals(db, user.id)
            assert second.created == 0
            assert second.skipped == 1

            messages = await service.list_messages(db, user.id)
            assert [item.kind for item in messages] == ["stale_goal"]
            assert "学会 Vue 3" in messages[0].content

        await engine.dispose()

    asyncio.run(scenario())
