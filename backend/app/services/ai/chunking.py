"""笔记分块：结构清洗 + 标题感知 + 段落聚合 + 重叠窗口

分块质量直接决定 RAG 的召回上限，因此：
1. 富文本笔记先转纯文本：编辑器存的是 HTML，直接按字符切会出现
   “从半个标签、半个 CSS 规则中间开始”的碎片，模型无法理解
2. 按空行切段并合并过短的段，避免标题行单独成块：只有标题的分块会因为
   命中关键词而排到最前，模型拿到的却是空内容
3. 超长段落按标点/换行边界硬切，不切断句子
4. 相邻块保留尾部重叠，缓解跨块语义断裂
"""

import hashlib
import re
from html import unescape

from app.core.config import settings

# 只有正文里出现这些标签时才当作富文本处理，纯 Markdown 笔记不动
_HTML_HINT = re.compile(r"(?i)<(p|div|h[1-6]|ul|ol|li|table|blockquote|pre|br|section|article)\b")
_BLOCK_TAG = re.compile(
    r"(?i)</?(p|div|h[1-6]|ul|ol|li|table|thead|tbody|tr|td|th|blockquote|pre|section|article|br|hr)\b[^>]*>"
)
_ANY_TAG = re.compile(r"(?i)<[^>]+>")
# 硬切时优先在这些字符之后断句
_SENTENCE_END = ("\n", "。", "！", "？", "；", ";", ".", "!", "?")

# 低于该长度的分块视为噪声（例如只剩一个标题、一处代码括号）
MIN_CHUNK_CHARS = 40


def content_hash(text: str) -> str:
    """计算分块内容指纹，用于增量更新判重"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数（中文按字符计，仅用于展示与配额预警）"""
    if not text:
        return 0
    return max(1, int(len(text) * 0.6))


def html_to_text(raw: str) -> str:
    """把编辑器保存的 HTML 转成可读纯文本

    笔记正文可能来自富文本编辑器，直接送入模型或分块会产生大量标签噪声，
    因此块级标签转成换行、行内标签直接去掉、实体字符还原。
    """
    if not raw or not _HTML_HINT.search(raw):
        return raw or ""
    text = _BLOCK_TAG.sub("\n", raw)
    text = _ANY_TAG.sub("", text)
    text = unescape(text).replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_into_chunks(
    text: str,
    max_chars: int | None = None,
    overlap: int | None = None,
) -> list[str]:
    """将长文本切分为带重叠的分块列表"""
    max_chars = max_chars or settings.AI_CHUNK_SIZE
    overlap = min(overlap if overlap is not None else settings.AI_CHUNK_OVERLAP, max_chars // 2)
    blocks = _split_blocks(text, max_chars)
    if not blocks:
        return []
    chunks = _pack_blocks(blocks, max_chars, overlap)
    # 过滤过短碎片；若整篇笔记本身就很短，则保留唯一分块
    filtered = [chunk for chunk in chunks if len(chunk) >= MIN_CHUNK_CHARS]
    return filtered or chunks[:1]


def _split_blocks(text: str, max_chars: int) -> list[str]:
    """按空行切段，合并过短段落，超长段落按边界硬切"""
    cleaned = html_to_text(re.sub(r"\r\n?", "\n", text or ""))
    normalized = cleaned.strip()
    if not normalized:
        return []

    blocks: list[str] = []
    pending = ""
    for part in re.split(r"\n{2,}", normalized):
        part = part.strip()
        if not part:
            continue
        # 短段（标题行、零散列表）先攒起来，和后面的正文合并成一个块，
        # 否则“# 标题”会单独成块并凭关键词命中排到最前
        if len(part) < MIN_CHUNK_CHARS and len(part) < max_chars // 4:
            pending = f"{pending}\n\n{part}" if pending else part
            continue
        merged = f"{pending}\n\n{part}" if pending else part
        pending = ""
        if len(merged) <= max_chars:
            blocks.append(merged)
        else:
            blocks.extend(_hard_split(merged, max_chars))

    if pending.strip():
        blocks.append(pending.strip())
    return blocks


def _hard_split(text: str, max_chars: int) -> list[str]:
    """超长文本硬切，尽量落在换行或句末，避免从半个词中间截断"""
    pieces: list[str] = []
    remainder = text
    while len(remainder) > max_chars:
        window = remainder[:max_chars]
        cut = max((window.rfind(mark) for mark in _SENTENCE_END), default=-1)
        # 断点太靠前会让块碎成小段，取不到合适位置就直接按长度切
        if cut < max_chars // 2:
            cut = max_chars - 1
        pieces.append(remainder[: cut + 1].strip())
        remainder = remainder[cut + 1 :].lstrip()
    if remainder:
        pieces.append(remainder.strip())
    return [piece for piece in pieces if piece]


def _pack_blocks(blocks: list[str], max_chars: int, overlap: int) -> list[str]:
    """贪心聚合段落，块间保留尾部重叠"""
    chunks: list[str] = []
    buffer = ""

    for block in blocks:
        candidate = f"{buffer}\n\n{block}" if buffer else block
        if len(candidate) <= max_chars:
            buffer = candidate
            continue

        if buffer:
            chunks.append(buffer)
            tail = buffer[-overlap:] if overlap > 0 else ""
            buffer = f"{tail}\n\n{block}" if tail else block
        else:
            buffer = block

        while len(buffer) > max_chars:
            chunks.append(buffer[:max_chars])
            buffer = buffer[max_chars:]

    if buffer.strip():
        chunks.append(buffer.strip())
    return chunks


def build_note_text(title: str, content: str | None) -> str:
    """把标题拼入正文，提升检索时标题关键词的权重"""
    body = (content or "").strip()
    if title and body:
        return f"# {title}\n\n{body}"
    return body or (title or "")
