"""长期记忆测试 — CRUD、上限、PII 脱敏、抽取去重与归属隔离"""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.models  # noqa: F401 — 确保全部模型注册到 Base.metadata
from app.core.config import settings
from app.core.database import Base
from app.models.ai import AIConversation, AIMessage
from app.models.user import User
from app.services.ai.memory_service import (
    MemoryHit,
    MemoryService,
    build_memory_context,
)
from app.services.ai.provider import AIProviderError, ChatResult
from conftest import register_user


class FakeProvider:
    """固定返回一条目标记忆的假模型"""

    async def chat(
        self, messages, model, temperature: float = 0.2, max_tokens=None
    ) -> ChatResult:
        return ChatResult(
            content='[{"type":"goal","content":"用户想学会 Vue 3","importance":4}]',
            tool_calls=[],
            usage={"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
            latency_ms=2,
        )


def test_memory_crud(client, auth):
    """手动记忆可创建、筛选、更新与删除"""
    created = client.post(
        "/api/ai/memories",
        json={"content": "我在学 Vue 3", "memory_type": "goal", "importance": 4},
        headers=auth,
    )
    assert created.status_code == 201
    memory = created.json()["data"]
    assert memory["source"] == "manual"

    listing = client.get(
        "/api/ai/memories", params={"memory_type": "goal"}, headers=auth
    ).json()["data"]
    assert listing["total"] == 1
    assert listing["items"][0]["content"] == "我在学 Vue 3"

    updated = client.put(
        f"/api/ai/memories/{memory['id']}",
        json={"importance": 5, "content": "我在认真学 Vue 3"},
        headers=auth,
    ).json()["data"]
    assert updated["importance"] == 5
    assert updated["content"] == "我在认真学 Vue 3"

    deleted = client.delete(f"/api/ai/memories/{memory['id']}", headers=auth)
    assert deleted.status_code == 200
    empty = client.get("/api/ai/memories", headers=auth).json()["data"]
    assert empty["total"] == 0


def test_memory_ownership_isolation(client):
    """他人不能修改或删除自己的记忆"""
    alice = register_user(client, "alice")
    bob = register_user(client, "bob")
    memory = client.post(
        "/api/ai/memories",
        json={"content": "我的目标", "memory_type": "goal"},
        headers=alice,
    ).json()["data"]

    response = client.put(
        f"/api/ai/memories/{memory['id']}",
        json={"content": "被改了"},
        headers=bob,
    )
    assert response.status_code == 400
    assert response.json()["code"] == 7008

    delete = client.delete(f"/api/ai/memories/{memory['id']}", headers=bob)
    assert delete.status_code == 400
    assert delete.json()["code"] == 7008


def test_memory_limit(client, auth, monkeypatch):
    """达到上限后拒绝新增"""
    monkeypatch.setattr(settings, "AI_MEMORY_MAX_PER_USER", 1)
    first = client.post(
        "/api/ai/memories", json={"content": "第一条"}, headers=auth
    )
    assert first.status_code == 201
    second = client.post(
        "/api/ai/memories", json={"content": "第二条"}, headers=auth
    )
    assert second.status_code == 400
    assert second.json()["code"] == 7009


def test_memory_context_masks_pii():
    """注入前必须脱敏手机号并标注来源类型"""
    context = build_memory_context(
        [
            MemoryHit(
                memory_id=1,
                memory_type="fact",
                content="我的手机号是 13800138000",
                importance=4,
                score=0.5,
            )
        ]
    )
    assert "<memory_context>" in context
    assert "[事实]" in context
    assert "13800138000" not in context


def test_extract_dedup_and_trim(tmp_path, monkeypatch):
    """同一会话重复抽取不产生重复记忆"""

    async def scenario() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'memory.db').as_posix()}",
            poolclass=NullPool,
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        async with session_factory() as db:
            user = User(username="memory", email="memory@example.com", password_hash="x")
            db.add(user)
            await db.commit()
            await db.refresh(user)
            conversation = AIConversation(
                user_id=user.id, title="学习计划", model="test", message_count=4
            )
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)
            for index in range(2):
                db.add(
                    AIMessage(
                        conversation_id=conversation.id,
                        role="user",
                        content=f"我想学会 Vue 3 的第 {index} 个理由",
                    )
                )
                db.add(
                    AIMessage(
                        conversation_id=conversation.id,
                        role="assistant",
                        content="好的，我们按计划推进。",
                    )
                )
            await db.commit()

            provider = FakeProvider()

            def no_embedding():
                raise AIProviderError("测试环境关闭向量")

            monkeypatch.setattr(
                "app.services.ai.memory_service.get_chat_provider", lambda: provider
            )
            monkeypatch.setattr(
                "app.services.ai.memory_service.get_embedding_provider", no_embedding
            )
            service = MemoryService()
            first = await service.extract_from_conversation(
                db, user.id, conversation.id
            )
            assert first["extracted"] == 1
            assert first["total"] == 1

            second = await service.extract_from_conversation(
                db, user.id, conversation.id
            )
            assert second["extracted"] == 0
            assert second["skipped_duplicates"] == 1
            assert second["total"] == 1

        await engine.dispose()

    asyncio.run(scenario())
