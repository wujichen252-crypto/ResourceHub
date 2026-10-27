"""混合检索：BM25 关键词召回 + 向量语义召回 + RRF 融合

设计取舍：
- 纯向量检索对中文专有名词、缩写不敏感；纯 BM25 又无法处理同义改写，
  因此采用双路召回后 RRF 融合，且任一路不可用时自动降级。
- 向量以 JSON 存储、在应用层计算余弦，万级 chunk 完全够用，
  后续可平滑迁移 pgvector / Qdrant 而不改动上层接口。
"""

import json
import logging
import math
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ai import NoteChunk
from app.models.note import Note
from app.services.ai.provider import AIProviderError, get_embedding_provider

logger = logging.getLogger(__name__)

_CJK_RUN = re.compile(r"[\u4e00-\u9fff]+")
_WORD = re.compile(r"[a-z0-9_]+")
_RRF_K = 60
# 总览类提问：用户想要的是“有哪些、讲什么”，而不是某一句原文
_OVERVIEW_PATTERN = re.compile(
    r"(总结|概括|汇总|概览|梳理|盘点|回顾|列出|有哪些|都写了|都记了).{0,10}"
    r"(笔记|记录|内容|文档|资料)"
    r"|(笔记|记录).{0,10}(总结|概括|有哪些|清单|大纲)"
)


@dataclass(slots=True)
class SearchHit:
    """检索命中的笔记片段"""

    chunk_id: int
    note_id: int
    note_title: str
    content: str
    score: float
    vector_score: float = 0.0
    bm25_score: float = 0.0


def tokenize(text: str) -> list[str]:
    """中英文混合分词：英文按词，中文按二元组（无需额外词典依赖）"""
    lowered = (text or "").lower()
    tokens = _WORD.findall(lowered)
    for run in _CJK_RUN.findall(lowered):
        if len(run) == 1:
            tokens.append(run)
        else:
            tokens.extend(run[i : i + 2] for i in range(len(run) - 1))
    return tokens


def _bm25_scores(docs: list[list[str]], query_tokens: list[str]) -> list[float]:
    """标准 BM25（k1=1.5, b=0.75）"""
    if not docs or not query_tokens:
        return [0.0] * len(docs)

    doc_count = len(docs)
    avg_len = sum(len(doc) for doc in docs) / doc_count or 1.0
    doc_freq: dict[str, int] = {}
    for doc in docs:
        for token in set(doc):
            doc_freq[token] = doc_freq.get(token, 0) + 1

    scores: list[float] = []
    for doc in docs:
        frequencies: dict[str, int] = {}
        for token in doc:
            frequencies[token] = frequencies.get(token, 0) + 1
        score = 0.0
        for token in query_tokens:
            tf = frequencies.get(token, 0)
            if not tf:
                continue
            df = doc_freq.get(token, 0)
            idf = math.log(1 + (doc_count - df + 0.5) / (df + 0.5))
            denominator = tf + 1.5 * (1 - 0.75 + 0.75 * len(doc) / avg_len)
            score += idf * tf * 2.5 / denominator
        scores.append(score)
    return scores


def _cosine(left: list[float], right: list[float]) -> float:
    """余弦相似度，向量维度不一致时视为无效"""
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    norm_left = math.sqrt(sum(a * a for a in left))
    norm_right = math.sqrt(sum(b * b for b in right))
    if norm_left == 0 or norm_right == 0:
        return 0.0
    return dot / (norm_left * norm_right)


def _rrf_weights(scores: list[float]) -> dict[int, float]:
    """把一路分数转换为 RRF 排名权重"""
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    return {index: 1.0 / (_RRF_K + rank + 1) for rank, index in enumerate(ranked)}


async def retrieve(
    db: AsyncSession,
    user_id: int,
    query: str,
    top_k: int = 4,
) -> list[SearchHit]:
    """检索与问题最相关的笔记片段"""
    if is_overview_query(query):
        return await retrieve_overview(db, user_id, limit=max(top_k * 2, 6))

    rows = await _load_candidates(db, user_id)
    if not rows or not query.strip():
        return []

    contents = [row[0].content for row in rows]
    bm25 = _bm25_scores([tokenize(text) for text in contents], tokenize(query))
    vector = await _vector_scores([row[0] for row in rows], query)

    weights = _rrf_weights(bm25)
    if vector is not None:
        for index, weight in _rrf_weights(vector).items():
            weights[index] = weights.get(index, 0.0) + weight

    # 相关度门槛：既无关键词命中、语义相似度又过低的分块视为无依据，
    # 否则模型会拿着无关片段自由发挥并给出假引用
    candidates = sorted(weights, key=lambda i: weights[i], reverse=True)
    ordered = [
        i
        for i in candidates
        if bm25[i] > 0 or (vector is not None and vector[i] >= settings.AI_MIN_VECTOR_SCORE)
    ][:top_k]
    return [
        SearchHit(
            chunk_id=rows[i][0].id,
            note_id=rows[i][0].note_id,
            note_title=rows[i][1],
            content=rows[i][0].content,
            score=round(weights[i], 6),
            vector_score=round(vector[i], 4) if vector is not None else 0.0,
            bm25_score=round(bm25[i], 4),
        )
        for i in ordered
    ]


def is_overview_query(query: str) -> bool:
    """判断是否属于「总结/概览我的笔记」这类总览型提问

    总览型问题靠关键词排序只会命中几个零散片段，覆盖不到多篇笔记，
    模型因此只能罗列标题并回答“片段里没提到具体内容”。
    """
    return bool(_OVERVIEW_PATTERN.search((query or "").lower()))


async def retrieve_overview(
    db: AsyncSession,
    user_id: int,
    limit: int = 6,
) -> list[SearchHit]:
    """总览检索：按更新时间倒序，取每篇笔记的开头分块

    每篇笔记取第一块（含标题与开篇正文），保证模型看到的是「每篇讲什么」，
    而不是同一篇里几段互不相干的原文。
    """
    result = await db.execute(
        select(NoteChunk, Note.title, Note.updated_at)
        .join(Note, Note.id == NoteChunk.note_id)
        .where(
            NoteChunk.user_id == user_id,
            Note.user_id == user_id,
            NoteChunk.chunk_index == 0,
        )
        .order_by(Note.updated_at.desc())
        .limit(limit)
    )

    hits: list[SearchHit] = []
    for index, (chunk, title, _updated) in enumerate(result.all()):
        hits.append(
            SearchHit(
                chunk_id=chunk.id,
                note_id=chunk.note_id,
                note_title=title,
                content=chunk.content,
                # 总览结果不按相关度排序，给一个递减值以保持前端展示顺序
                score=round(max(0.1, 0.9 - index * 0.05), 4),
            )
        )
    return hits


async def _load_candidates(
    db: AsyncSession, user_id: int
) -> list[tuple[NoteChunk, str]]:
    """加载候选分块，附带所属笔记标题"""
    result = await db.execute(
        select(NoteChunk, Note.title)
        .join(Note, Note.id == NoteChunk.note_id)
        .where(NoteChunk.user_id == user_id, Note.user_id == user_id)
        .order_by(NoteChunk.updated_at.desc())
        .limit(settings.AI_RETRIEVAL_CANDIDATES)
    )
    return list(result.all())


async def _vector_scores(chunks: list[NoteChunk], query: str) -> list[float] | None:
    """向量召回；未配置、无向量或调用失败时返回 None，由调用方降级为 BM25"""
    vectors = [_parse_vector(chunk.embedding) for chunk in chunks]
    if not any(vectors):
        return None
    try:
        provider = get_embedding_provider()
        query_vector = (await provider.embed([query]))[0]
        if not query_vector:
            return None
        return [_cosine(query_vector, vector) for vector in vectors]
    except (AIProviderError, IndexError) as exc:
        logger.warning("向量召回降级为 BM25：%s", exc)
        return None


def _parse_vector(raw: str | None) -> list[float]:
    """解析数据库中 JSON 数组形态的向量"""
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [float(item) for item in value if isinstance(item, (int, float))]

