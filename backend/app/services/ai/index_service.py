"""笔记索引服务：分块 + 向量化 + 落库

策略：
- 重建按笔记粒度删除旧块后整体写入，保证 chunk_index 连续
- 向量服务不可用时仍写入分块（embedding 为空），检索自动降级为 BM25
- 分批向量化，避免单次请求过大触发上游限流
"""

import asyncio
import json
import logging

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.ai import NoteChunk
from app.models.note import Note
from app.services.ai.chunking import (
    build_note_text,
    content_hash,
    estimate_tokens,
    split_into_chunks,
)
from app.services.ai.provider import AIProviderError, get_embedding_provider

logger = logging.getLogger(__name__)

# 同一用户的索引操作串行执行：自动增量索引与手动重建可能同时发生，
# 两边都在删改同一批分块，MySQL 会因互相等待锁而报 1213 死锁
_LOCKS: dict[int, tuple[asyncio.AbstractEventLoop, asyncio.Lock]] = {}


def _user_lock(user_id: int) -> asyncio.Lock:
    """按用户取锁；换事件循环（如测试）时重建，避免锁绑定到旧循环"""
    loop = asyncio.get_running_loop()
    entry = _LOCKS.get(user_id)
    if entry is None or entry[0] is not loop:
        entry = (loop, asyncio.Lock())
        _LOCKS[user_id] = entry
    return entry[1]


def _is_deadlock(exc: OperationalError) -> bool:
    """MySQL 1213 = 死锁，属于可重试的瞬时错误"""
    return "1213" in str(getattr(exc, "orig", exc))


class IndexService:
    """负责笔记到检索分块的转换"""

    async def rebuild(
        self, db: AsyncSession, user_id: int, note_ids: list[int] | None = None
    ) -> dict:
        """重建指定笔记（或全部笔记）的索引"""
        async with _user_lock(user_id):
            return await self._rebuild_all(db, user_id, note_ids)

    async def _rebuild_all(
        self, db: AsyncSession, user_id: int, note_ids: list[int] | None
    ) -> dict:
        query = select(Note).where(Note.user_id == user_id)
        if note_ids:
            query = query.where(Note.id.in_(note_ids))
        notes = (await db.execute(query.order_by(Note.id))).scalars().all()

        indexed_notes = 0
        indexed_chunks = 0
        skipped_notes = 0
        embedding_ok = True

        for note in notes:
            try:
                chunks = await self._rebuild_one(db, note)
                # 逐篇提交：整批写完再提交会让事务过大，远端数据库等锁超时后
                # 会直接断开连接（Lost connection），且一失败就全篇重来
                await db.commit()
            except OperationalError as exc:
                await db.rollback()
                logger.warning("单篇索引失败，已跳过 note_id=%s：%s", note.id, exc)
                skipped_notes += 1
                continue
            if not chunks:
                skipped_notes += 1
                continue
            if any(chunk.embedding is None for chunk in chunks):
                embedding_ok = False
            indexed_notes += 1
            indexed_chunks += len(chunks)

        message = (
            "AI 已重新读取你的笔记"
            if embedding_ok
            else "AI 已重新读取笔记；智能匹配服务暂时不可用，已改用关键词查找"
        )
        return {
            "indexed_notes": indexed_notes,
            "indexed_chunks": indexed_chunks,
            "skipped_notes": skipped_notes,
            "embedding_ok": embedding_ok,
            "message": message,
        }

    async def index_note(self, db: AsyncSession, user_id: int, note_id: int) -> bool:
        """增量索引单篇笔记；笔记不存在时返回 False

        笔记自动保存会连续触发索引，并发重写同一篇笔记可能撞上
        uq_note_chunks_note_index 唯一约束或数据库死锁，回滚后重试即可收敛。
        """
        async with _user_lock(user_id):
            note = await self._load_note(db, user_id, note_id)
            if note is None:
                return False

            for attempt in range(3):
                try:
                    chunks = await self._rebuild_one(db, note)
                    await db.commit()
                    return bool(chunks)
                except (IntegrityError, OperationalError) as exc:
                    if isinstance(exc, OperationalError) and not _is_deadlock(exc):
                        raise
                    await db.rollback()
                    if attempt == 2:
                        raise
                    # 回滚会让 ORM 实例过期，重试前必须重新加载
                    note = await self._load_note(db, user_id, note_id)
                    if note is None:
                        return False
            return False

    @staticmethod
    async def _load_note(db: AsyncSession, user_id: int, note_id: int) -> Note | None:
        """按归属加载笔记，避免索引到他人数据"""
        result = await db.execute(
            select(Note).where(Note.id == note_id, Note.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def _rebuild_one(self, db: AsyncSession, note: Note) -> list[NoteChunk]:
        """重建单篇笔记的分块，返回新写入的分块列表"""
        await db.execute(delete(NoteChunk).where(NoteChunk.note_id == note.id))
        text = build_note_text(note.title, note.content)
        pieces = split_into_chunks(text)
        if not pieces:
            return []

        vectors, ok = await self._embed(pieces)
        chunks: list[NoteChunk] = []
        for index, piece in enumerate(pieces):
            chunk = NoteChunk(
                user_id=note.user_id,
                note_id=note.id,
                chunk_index=index,
                content=piece,
                content_hash=content_hash(piece),
                token_count=estimate_tokens(piece),
                # 向量保留 5 位小数足够计算余弦，同时把单行体积压掉一半以上，
                # 避免大笔记插入时超出远端数据库的包大小与超时限制
                embedding=(
                    json.dumps([round(value, 5) for value in vectors[index]])
                    if ok
                    else None
                ),
                embedding_model=settings.AI_EMBEDDING_MODEL if ok else None,
            )
            db.add(chunk)
            chunks.append(chunk)
            # 每 10 块 flush 一次，避免单次提交携带过多 20KB 级向量
            if len(chunks) % 10 == 0:
                await db.flush()
        await db.flush()
        return chunks

    async def _embed(self, texts: list[str]) -> tuple[list[list[float]], bool]:
        """分批向量化；任一批失败则整体降级（不写入残缺向量）"""
        try:
            provider = get_embedding_provider()
        except AIProviderError as exc:
            logger.warning("向量服务未配置，索引降级：%s", exc)
            return [[] for _ in texts], False

        vectors: list[list[float]] = []
        batch_size = max(1, settings.AI_EMBEDDING_BATCH_SIZE)
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            try:
                batch_vectors = await provider.embed(batch)
            except AIProviderError as exc:
                logger.warning("向量化失败，索引降级：%s", exc)
                return [[] for _ in texts], False
            if len(batch_vectors) != len(batch):
                logger.warning("向量返回数量不匹配，索引降级")
                return [[] for _ in texts], False
            vectors.extend(batch_vectors)
        return vectors, True


async def index_note_in_background(user_id: int, note_id: int) -> None:
    """笔记保存后的后台增量索引入口（由 FastAPI BackgroundTasks 调用）

    使用独立会话：请求会话在响应返回后即关闭，不能复用。
    未配置模型密钥时直接跳过；索引失败只记日志，不影响已经成功的笔记保存。
    """
    if not settings.ai_configured:
        return

    async with SessionLocal() as db:
        try:
            await IndexService().index_note(db, user_id, note_id)
        except Exception:
            await db.rollback()
            logger.exception("笔记增量索引失败 note_id=%s", note_id)
