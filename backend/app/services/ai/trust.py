"""回答可信度评估：纯函数计算，零 AI 调用

三因子加权（详见 docs/回答可信度可视化与引用溯源高亮设计方案.md §2.2）：
- coverage 依据覆盖度：回答中事实性句子被 [n] 标注的比例
- quality 检索质量：被引用片段的最大向量相似度，线性映射；BM25 降级时取中性值
- validity 引用有效性：引用编号是否真实存在于检索结果（幻觉编号扣减）

模式判定先行：拒答 / 基于记忆 / 通用知识三种回答不评分，只给模式徽章。
"""

import re

# 引用编号：仅匹配纯数字形态，避免误伤 Markdown 链接 [text](url)
_INDEX_PATTERN = re.compile(r"\[(\d+)\]")
# 切句：中英文句末标点 + 换行
_SENTENCE_SPLIT = re.compile(r"[。！？!?\n]+")
# 短于此长度的句子视为开场白/连接语，不计入覆盖度分母
_MIN_SENTENCE_LEN = 6

# 三因子权重与分级阈值（设计文档 §2.2）
COVERAGE_WEIGHT = 0.5
QUALITY_WEIGHT = 0.3
VALIDITY_WEIGHT = 0.2
HIGH_THRESHOLD = 70
MID_THRESHOLD = 45

# 向量相似度线性映射区间：cosine < 0.30 记 0 分，> 0.75 记满分
QUALITY_FLOOR = 0.30
QUALITY_CEIL = 0.75
# 向量召回降级（BM25-only 或被引用片段无向量）时质量因子取中性值
NEUTRAL_QUALITY = 0.5


def extract_indices(answer: str) -> list[int]:
    """提取回答中的引用编号（去重保序）"""
    seen: list[int] = []
    for match in _INDEX_PATTERN.finditer(answer or ""):
        index = int(match.group(1))
        if index not in seen:
            seen.append(index)
    return seen


def split_sentences(text: str) -> list[str]:
    """按句切分，剔除空白段"""
    return [part.strip() for part in _SENTENCE_SPLIT.split(text or "") if part.strip()]


def _coverage(answer: str) -> tuple[float, int, int]:
    """依据覆盖度：含引用编号的事实性句子占比"""
    sentences = [s for s in split_sentences(answer) if len(s) >= _MIN_SENTENCE_LEN]
    if not sentences:
        return 0.0, 0, 0
    cited = sum(1 for s in sentences if _INDEX_PATTERN.search(s))
    return cited / len(sentences), len(sentences), cited


def _quality(hits: list, cited_indices: list[int]) -> tuple[float, bool]:
    """检索质量：被引用片段的最大向量相似度映射到 [0,1]；降级时取中性值

    降级判定：所有被引用片段的向量分均为 0（检索时向量不可用或片段无向量）。
    返回 (质量分, 是否降级)。
    """
    cited_hits = [hit for pos, hit in enumerate(hits, start=1) if pos in cited_indices]
    if not cited_hits:
        return 0.0, False
    max_vector = max(getattr(hit, "vector_score", 0.0) or 0.0 for hit in cited_hits)
    if max_vector <= 0:
        return NEUTRAL_QUALITY, True
    mapped = (max_vector - QUALITY_FLOOR) / (QUALITY_CEIL - QUALITY_FLOOR)
    return max(0.0, min(1.0, mapped)), False


def compute_trust(answer: str, hits: list, use_rag: bool, has_memory: bool) -> dict:
    """计算回答可信度报告

    hits 为检索命中列表（retrieval.SearchHit），按序号 [1..n] 与回答编号对应。
    """
    if use_rag and not hits and not has_memory:
        return {"mode": "refusal", "score": None, "level": "none",
                "factors": None, "cited_indices": [], "invalid_indices": [],
                "sentence_count": 0, "cited_sentence_count": 0, "retrieval_degraded": False}
    if use_rag and not hits and has_memory:
        return {"mode": "memory", "score": None, "level": "neutral",
                "factors": None, "cited_indices": [], "invalid_indices": [],
                "sentence_count": 0, "cited_sentence_count": 0, "retrieval_degraded": False}
    if not use_rag or not hits:
        return {"mode": "general", "score": None, "level": "neutral",
                "factors": None, "cited_indices": [], "invalid_indices": [],
                "sentence_count": 0, "cited_sentence_count": 0, "retrieval_degraded": False}

    cited_indices = extract_indices(answer)
    valid = {i for i in cited_indices if 1 <= i <= len(hits)}
    invalid = [i for i in cited_indices if i not in valid]
    validity = len(valid) / len(cited_indices) if cited_indices else 0.0

    coverage, sentence_count, cited_sentence_count = _coverage(answer)
    quality, degraded = _quality(hits, valid)

    score = round(100 * (
        COVERAGE_WEIGHT * coverage
        + QUALITY_WEIGHT * quality
        + VALIDITY_WEIGHT * validity
    ))
    if score >= HIGH_THRESHOLD and validity >= 1.0 and coverage > 0:
        level = "high"
    elif score >= MID_THRESHOLD:
        # 引用有效性缺失（幻觉编号）时等级封顶为「中」
        level = "mid"
    else:
        level = "low"

    return {
        "mode": "rag",
        "score": score,
        "level": level,
        "factors": {
            "coverage": round(coverage, 3),
            "quality": round(quality, 3),
            "validity": round(validity, 3),
        },
        "cited_indices": sorted(valid),
        "invalid_indices": invalid,
        "sentence_count": sentence_count,
        "cited_sentence_count": cited_sentence_count,
        "retrieval_degraded": degraded,
    }
