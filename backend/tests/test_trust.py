"""回答可信度测试 — 三因子计算、模式判定、SSE 事件顺序与落库"""

import asyncio
import json

import pytest
from conftest import register_user
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.models  # noqa: F401 — 确保全部模型注册到 Base.metadata
from app.core.config import settings
from app.core.database import Base
from app.models.ai import NoteChunk
from app.models.note import Note
from app.models.user import User
from app.services.ai.retrieval import SearchHit
from app.services.ai.trust import compute_trust, extract_indices, split_sentences


class FakeHit:
    """trust 计算只需 vector_score 字段，不依赖 ORM"""

    def __init__(self, vector_score: float):
        self.vector_score = vector_score


def _hits(*vector_scores: float) -> list:
    return [FakeHit(v) for v in vector_scores]


# ── 纯函数：模式判定 ────────────────────────────────────────────

def test_refusal_mode_when_no_hits_and_no_memory():
    report = compute_trust("回答", [], use_rag=True, has_memory=False)
    assert report["mode"] == "refusal"
    assert report["level"] == "none"
    assert report["score"] is None


def test_memory_mode_when_no_hits_but_has_memory():
    report = compute_trust("回答", [], use_rag=True, has_memory=True)
    assert report["mode"] == "memory"
    assert report["level"] == "neutral"


def test_general_mode_when_rag_disabled():
    report = compute_trust("回答", _hits(0.8), use_rag=False, has_memory=False)
    assert report["mode"] == "general"
    assert report["level"] == "neutral"


# ── 纯函数：三因子 ──────────────────────────────────────────────

def test_high_trust_with_full_coverage():
    """全部句子带有效引用且向量相似度高 → 高可信"""
    answer = "Cache-Control 决定缓存策略[1]。Expires 是过期时间戳[2]。两者可以配合使用[1][2]。"
    report = compute_trust(answer, _hits(0.82, 0.75), use_rag=True, has_memory=False)
    assert report["mode"] == "rag"
    assert report["level"] == "high"
    assert report["factors"]["coverage"] == 1.0
    assert report["factors"]["validity"] == 1.0
    assert report["cited_indices"] == [1, 2]


def test_low_trust_without_any_citation():
    """RAG 模式但回答完全没有标注 → 低可信（coverage 与 validity 均为 0）"""
    answer = "这是一个没有任何来源标注的回答句子，内容比较长，足够被计为事实性句子。"
    report = compute_trust(answer, _hits(0.8), use_rag=True, has_memory=False)
    assert report["level"] == "low"
    assert report["factors"]["coverage"] == 0.0


def test_hallucinated_index_caps_level_at_mid():
    """出现幻觉编号（只有 2 个片段却标了 [3]）→ 等级不能是「高」并列出无效编号"""
    answer = "第一点来自笔记[1]。第二点同样有依据[2]。第三点标注了不存在的来源[3]。"
    report = compute_trust(answer, _hits(0.8, 0.8), use_rag=True, has_memory=False)
    assert report["invalid_indices"] == [3]
    assert report["level"] != "high"


def test_quality_neutral_when_vector_degraded():
    """向量召回降级（被引用片段向量分全为 0）→ 质量因子取中性值并标记降级"""
    answer = "这是第一条有依据的结论[1]。这是第二条有依据的结论[1]。"
    report = compute_trust(answer, _hits(0.0), use_rag=True, has_memory=False)
    assert report["factors"]["quality"] == 0.5
    assert report["retrieval_degraded"] is True


def test_quality_scales_with_vector_score():
    """向量相似度 0.52 → 映射 (0.52-0.30)/(0.75-0.30) ≈ 0.489"""
    answer = "这是一条有依据的结论，并且足够长[1]。"
    report = compute_trust(answer, _hits(0.52), use_rag=True, has_memory=False)
    assert report["factors"]["quality"] == round((0.52 - 0.30) / (0.75 - 0.30), 3)


def test_coverage_ignores_short_sentences():
    """短于 6 字的句子视为开场白，不计入覆盖度分母"""
    answer = "好的。这是一个带依据的完整句子[1]。"
    report = compute_trust(answer, _hits(0.8), use_rag=True, has_memory=False)
    assert report["sentence_count"] == 1
    assert report["cited_sentence_count"] == 1
    assert report["factors"]["coverage"] == 1.0


# ── 纯函数：工具函数 ────────────────────────────────────────────

def test_extract_indices_deduplicates_and_keeps_order():
    assert extract_indices("开头[1]中间[2]重复[1]结尾") == [1, 2]


def test_extract_indices_ignores_markdown_links():
    """链接形态 [text](url) 不应被当作引用编号"""
    assert extract_indices("[说明](http://example.com)") == []


def test_split_sentences_by_cjk_and_newline():
    assert split_sentences("第一句。第二句！第三句？\n第四句") == [
        "第一句", "第二句", "第三句", "第四句",
    ]


def test_search_hit_compatible_with_compute_trust():
    """真实 SearchHit（slots dataclass）可直接参与计算"""
    hit = SearchHit(chunk_id=1, note_id=1, note_title="t", content="c",
                    score=0.02, vector_score=0.66)
    report = compute_trust("这是一条带依据的完整回答句子[1]。", [hit], True, False)
    assert report["factors"]["quality"] == round((0.66 - 0.30) / 0.45, 3)


# ── 集成：SSE 事件顺序与落库 ────────────────────────────────────

class FakeStreamProvider:
    """假流式模型：固定输出带引用的回答；embed 返回固定向量供检索计算"""

    async def stream_chat(self, messages, model, temperature=0.2):
        for token in ("缓存策略由", "Cache-Control 决定[1]。", "同时注意过期时间[2]。"):
            yield type("StreamEvent", (), {"kind": "token", "text": token})()
        yield type("StreamEvent", (), {
            "kind": "done",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        })()

    async def embed(self, texts):
        return [[0.1] * 8 for _ in texts]


@pytest.fixture()
def chat_provider(client, auth, monkeypatch):
    """开启 AI 可用开关、关闭后台记忆抽取、替换 chat 与检索的模型客户端"""
    monkeypatch.setattr(settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "AI_MEMORY_EXTRACT_ENABLED", False)
    provider = FakeStreamProvider()
    monkeypatch.setattr("app.services.ai.chat_service.get_chat_provider", lambda: provider)
    # 检索的查询向量也走假服务，保证 BM25/向量双路召回不触网
    monkeypatch.setattr("app.services.ai.retrieval.get_embedding_provider", lambda: provider)
    return provider


async def _seed_notes(db_url: str) -> None:
    """给 alice 造一篇笔记（含向量分块），让 RAG 检索有命中"""
    engine = create_async_engine(db_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        user = (await db.execute(
            User.__table__.select().where(User.username == "alice")
        )).first()
        note = Note(user_id=user.id, title="缓存策略", content="缓存策略由 Cache-Control 控制")
        db.add(note)
        await db.flush()
        db.add_all([
            NoteChunk(
                user_id=user.id, note_id=note.id, chunk_index=0,
                content="缓存策略由 Cache-Control 控制，可配置 max-age 与 no-store",
                embedding=json.dumps([0.1] * 8),
            ),
            NoteChunk(
                user_id=user.id, note_id=note.id, chunk_index=1,
                content="Expires 设置过期时间戳，与 Cache-Control 配合使用",
                embedding=json.dumps([0.1] * 8),
            ),
        ])
        await db.commit()
    await engine.dispose()


def _parse_sse_events(raw_text: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for frame in raw_text.split("\n\n"):
        event, data = "", ""
        for line in frame.split("\n"):
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data += line[5:]
        if event and data:
            events.append((event, json.loads(data)))
    return events


def test_chat_stream_emits_trust_before_done(client, auth, chat_provider, db_url):
    """trust 事件位于最后一个 token 之后、done 之前，且带完整报告"""
    asyncio.run(_seed_notes(db_url))
    response = client.post(
        "/api/ai/chat",
        json={"message": "什么是缓存策略？", "use_rag": True},
        headers=auth,
    )
    events = _parse_sse_events(response.text)
    names = [name for name, _ in events]

    assert "trust" in names
    assert names[-1] == "done"
    assert names.index("trust") == len(names) - 2  # trust 紧邻 done 之前

    trust = next(d for n, d in events if n == "trust")
    assert trust["mode"] == "rag"
    assert trust["cited_indices"] == [1, 2]
    assert trust["factors"]["validity"] == 1.0
    assert trust["level"] == "high"


def test_chat_persists_trust_json(client, auth, chat_provider, db_url):
    """回答落库时写入 trust_json，历史消息接口返回解析后的 trust"""
    asyncio.run(_seed_notes(db_url))
    client.post("/api/ai/chat", json={"message": "什么是缓存策略？", "use_rag": True},
                headers=auth)

    conversations = client.get("/api/ai/conversations", headers=auth).json()["data"]["items"]
    messages = client.get(
        f"/api/ai/conversations/{conversations[0]['id']}/messages", headers=auth
    ).json()["data"]["items"]

    assistant = [m for m in messages if m["role"] == "assistant"]
    assert len(assistant) == 1
    assert assistant[0]["trust"] is not None
    assert assistant[0]["trust"]["mode"] == "rag"
    # 用户消息没有可信度报告
    users = [m for m in messages if m["role"] == "user"]
    assert users[0]["trust"] is None


def test_chat_refusal_emits_trust_none_level(client, auth, chat_provider, monkeypatch):
    """无检索依据时拒答分支也发出 trust（mode=refusal）"""
    # 检索不到任何命中：模拟空库
    from app.services.ai import chat_service as chat_module

    async def _no_hits(*args, **kwargs):
        return []

    monkeypatch.setattr(chat_module, "retrieve", _no_hits)
    response = client.post(
        "/api/ai/chat",
        json={"message": "完全查不到的问题", "use_rag": True},
        headers=auth,
    )
    events = _parse_sse_events(response.text)
    trust = next(d for n, d in events if n == "trust")
    assert trust["mode"] == "refusal"
    assert trust["level"] == "none"


def test_general_mode_without_rag(client, auth, chat_provider):
    """关闭 RAG 时回答按通用知识模式处理，不评分"""
    response = client.post(
        "/api/ai/chat",
        json={"message": "任意问题", "use_rag": False},
        headers=auth,
    )
    events = _parse_sse_events(response.text)
    trust = next(d for n, d in events if n == "trust")
    assert trust["mode"] == "general"
    assert trust["score"] is None
