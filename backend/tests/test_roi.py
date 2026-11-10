"""ROI 看板聚合回归测试 — 锁定 /api/roi/* 响应结构与金额换算、健康度分级契约"""

import asyncio
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models.ai import AIConversation, AIMessage, AIUsageLog, NoteChunk
from app.models.user import User

PRICES = json.dumps({"m1": {"input": 0.001, "output": 0.002}})


def _seed(db_url: str, prompt_id: int | None, note_id: int):
    """直接向测试库写入计量/引用/分块数据（与 client 同一 tmp 库）"""

    async def _run() -> None:
        engine = create_async_engine(db_url, poolclass=NullPool)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            user_id = (await session.execute(select(User).where(User.username == "alice"))).scalar_one().id

            # 计量流水：m1 已计价（1000×0.001/千 + 500×0.002/千 = 0.002 元），m2 未计价
            session.add_all([
                AIUsageLog(user_id=user_id, scene="chat", model="m1",
                           prompt_tokens=1000, completion_tokens=500, total_tokens=1500,
                           latency_ms=1000, success=True),
                AIUsageLog(user_id=user_id, scene="chat", model="m2",
                           prompt_tokens=0, completion_tokens=0, total_tokens=100,
                           latency_ms=500, success=True),
                AIUsageLog(user_id=user_id, scene="eval", model="m1",
                           prompt_tokens=0, completion_tokens=0, total_tokens=300,
                           latency_ms=800, success=True, prompt_id=prompt_id),
                AIUsageLog(user_id=user_id, scene="chat", model="m1",
                           prompt_tokens=0, completion_tokens=0, total_tokens=50,
                           latency_ms=0, success=False, error_code="upstream_error"),
            ])

            # 笔记引用：笔记 A 被 AI 引用 3 次 → 高产出
            conv = AIConversation(user_id=user_id, title="问答", model="m1")
            session.add(conv)
            await session.flush()
            session.add(AIMessage(
                conversation_id=conv.id, role="assistant", content="答案",
                citations=json.dumps([{"index": 1, "note_id": note_id, "note_title": "A"}]),
            ))

            # 分块：笔记 A 索引 2000 token
            session.add(NoteChunk(
                user_id=user_id, note_id=note_id, chunk_index=0,
                content="a" * 10, token_count=2000,
            ))
            await session.commit()
        await engine.dispose()

    asyncio.run(_run())


def _seed_prompt_data(db_url: str, prompt_id: int):
    """提示词级数据：评测得分 + 已完成优化会话（提分）"""

    async def _run() -> None:
        from app.models.ai import (
            PromptEvalCase,
            PromptEvalResult,
            PromptEvalSuite,
            PromptOptimizationRun,
        )

        engine = create_async_engine(db_url, poolclass=NullPool)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            user_id = (await session.execute(select(User).where(User.username == "alice"))).scalar_one().id
            suite = PromptEvalSuite(user_id=user_id, prompt_id=prompt_id, name="套件")
            session.add(suite)
            await session.flush()
            case = PromptEvalCase(suite_id=suite.id, variables="{}")
            session.add(case)
            await session.flush()
            session.add(PromptEvalResult(suite_id=suite.id, case_id=case.id, output="out", score=90.0))
            session.add(PromptOptimizationRun(
                user_id=user_id, prompt_id=prompt_id, suite_id=suite.id,
                status="completed", baseline_score=70.0, candidate_score=85.0,
            ))
            await session.commit()
        await engine.dispose()

    asyncio.run(_run())


def test_roi_summary_cost_and_distribution(client, auth, db_url, monkeypatch):
    monkeypatch.setattr(settings, "AI_MODEL_PRICES", PRICES)
    note = client.post("/api/notes", json={"title": "A", "content": "x"}, headers=auth).json()["data"]
    _seed(db_url, None, note["id"])

    resp = client.get("/api/roi/summary", headers=auth)
    assert resp.status_code == 200
    data = resp.json()["data"]

    assert data["total_tokens"] == 1500 + 100 + 300 + 50
    assert data["total_calls"] == 4
    assert data["success_rate"] == 0.75
    assert data["cost_total"] == 0.002  # 仅 m1 计价部分
    assert data["unpriced_tokens"] == 100
    scenes = {s["scene"]: s["tokens"] for s in data["by_scene"]}
    assert scenes["chat"] == 1650 and scenes["eval"] == 300
    assert data["quota_limit"] == settings.AI_DAILY_TOKEN_QUOTA


def test_roi_trend_points(client, auth, db_url, monkeypatch):
    monkeypatch.setattr(settings, "AI_MODEL_PRICES", PRICES)
    note = client.post("/api/notes", json={"title": "A", "content": "x"}, headers=auth).json()["data"]
    _seed(db_url, None, note["id"])

    data = client.get("/api/roi/trend", headers=auth).json()["data"]
    assert len(data["points"]) == 30
    today = data["points"][-1]
    assert today["calls"] == 4 and today["tokens"] == 1950 and today["failures"] == 1
    assert today["scenes"]["chat"] == 1650
    assert today["cost"] == 0.002
    assert sum(p["tokens"] for p in data["points"]) == 1950  # 缺失日补 0


def test_roi_notes_grades(client, auth, db_url, monkeypatch):
    monkeypatch.setattr(settings, "AI_MODEL_PRICES", PRICES)
    note = client.post("/api/notes", json={"title": "A", "content": "x"}, headers=auth).json()["data"]
    _seed(db_url, None, note["id"])

    data = client.get("/api/roi/notes", headers=auth).json()["data"]
    assert len(data) == 1
    item = data[0]
    assert item["note_id"] == note["id"]
    assert item["citations"] == 1  # 单条消息引用一次
    assert item["index_tokens"] == 2000
    assert item["index_cost"] is None  # 价格表未配置 embedding 模型 → 未计价
    assert item["grade"] == "normal"  # 引用 1 次


def test_roi_notes_high_yield_and_cost_fields(client, auth, db_url, monkeypatch):
    monkeypatch.setattr(settings, "AI_MODEL_PRICES", json.dumps({
        "m1": {"input": 0.001, "output": 0.002},
        settings.AI_EMBEDDING_MODEL: {"input": 0.0002, "output": 0},
    }))
    note = client.post("/api/notes", json={"title": "A", "content": "x"}, headers=auth).json()["data"]
    _seed(db_url, None, note["id"])

    item = client.get("/api/roi/notes", headers=auth).json()["data"][0]
    assert item["index_cost"] == round(2000 / 1000 * 0.0002, 4)
    # ROI 评分 = 1 次引用 × 10 − 2000/1000 = 8.0
    assert item["roi_score"] == 8.0


def test_roi_prompts(client, auth, db_url, monkeypatch):
    monkeypatch.setattr(settings, "AI_MODEL_PRICES", PRICES)
    prompt = client.post(
        "/api/prompts", json={"title": "代码审查", "content": "review"}, headers=auth
    ).json()["data"]
    client.post(f"/api/prompts/{prompt['id']}/use", headers=auth)
    _seed(db_url, prompt["id"], 0)
    _seed_prompt_data(db_url, prompt["id"])

    data = client.get("/api/roi/prompts", headers=auth).json()["data"]
    assert len(data) == 1
    item = data[0]
    assert item["usage_count"] == 1
    assert item["quality_score"] == 90.0
    assert item["score_gain"] == 15.0  # 85 − 70
    # 本用例未造 optimize 场景流水 → 优化投入 0，ROI = 1 × 90 / (1 + 0)
    assert item["roi_score"] == 90.0


def test_roi_scenes(client, auth, db_url, monkeypatch):
    monkeypatch.setattr(settings, "AI_MODEL_PRICES", PRICES)
    note = client.post("/api/notes", json={"title": "A", "content": "x"}, headers=auth).json()["data"]
    _seed(db_url, None, note["id"])

    data = client.get("/api/roi/scenes", headers=auth).json()["data"]
    scenes = {s["scene"]: s for s in data}
    assert scenes["chat"]["tokens"] == 1650
    assert scenes["chat"]["calls"] == 3
    assert scenes["eval"]["cost"] == 0.0 and scenes["chat"]["cost"] == 0.002


def test_roi_requires_auth(client):
    assert client.get("/api/roi/summary").status_code == 401


def test_roi_user_isolation(client, auth, db_url, monkeypatch):
    from conftest import register_user

    monkeypatch.setattr(settings, "AI_MODEL_PRICES", PRICES)
    note = client.post("/api/notes", json={"title": "A", "content": "x"}, headers=auth).json()["data"]
    _seed(db_url, None, note["id"])

    bob = register_user(client, "bob_roi")
    data = client.get("/api/roi/summary", headers=bob).json()["data"]
    assert data["total_tokens"] == 0 and data["by_scene"] == []
    assert client.get("/api/roi/notes", headers=bob).json()["data"] == []


def test_roi_invalid_window_fallback(client, auth):
    resp = client.get("/api/roi/summary", params={"days": 9999}, headers=auth)
    assert resp.status_code == 200
    assert resp.json()["data"]["days"] == 30
