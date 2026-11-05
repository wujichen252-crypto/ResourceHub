"""
搜索服务薄适配层 — 封装 Meilisearch（httpx 直连，零新增依赖）

设计约束（见 docs/cloud-kb-iteration-plan-v2-oss.md）：
- 上游可替换：业务层只依赖本模块的 index/search/delete 三个能力
- 失败不影响主流程：所有写操作只记日志；查询失败返回 None 由调用方降级 LIKE
- 数据隔离：所有查询强制 filter `user_id = <当前用户>`，绝不跨用户召回
"""

import asyncio
import html
import json
import logging
import re

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.note import Note

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"[\s\u00a0]+")
_index_ready = False
_index_lock = asyncio.Lock()


def strip_html(raw: str | None) -> str:
    """HTML 快照转纯文本：去标签 + 实体还原 + 空白归一，避免标签与 &nbsp; 污染分词"""
    if not raw:
        return ""
    text = html.unescape(_TAG_RE.sub(" ", raw))
    return _SPACE_RE.sub(" ", text).strip()


class SearchService:
    """Meilisearch 适配层；未启用时所有方法安全短路"""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    # ── 基础设施 ──

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {}
            if settings.MEILI_MASTER_KEY:
                headers["Authorization"] = f"Bearer {settings.MEILI_MASTER_KEY}"
            self._client = httpx.AsyncClient(
                base_url=settings.MEILI_URL.rstrip("/"),
                headers=headers,
                timeout=settings.MEILI_TIMEOUT,
            )
        return self._client

    async def ensure_index(self) -> bool:
        """确保索引与检索配置存在（进程内只执行一次）"""
        global _index_ready
        if _index_ready:
            return True
        async with _index_lock:
            if _index_ready:
                return True
            client = self._get_client()
            # 索引不存在时创建（已存在返回 409，视为成功）
            resp = await client.post(
                "/indexes",
                json={"uid": settings.MEILI_INDEX, "primaryKey": "id"},
            )
            if resp.status_code not in (200, 201, 202, 409):
                logger.warning("创建搜索索引失败 status=%s body=%s", resp.status_code, resp.text[:200])
                return False
            # 中文分词、过滤与排序字段
            resp = await client.patch(
                f"/indexes/{settings.MEILI_INDEX}/settings",
                json={
                    "searchableAttributes": ["title", "content_text", "tags"],
                    "filterableAttributes": ["user_id", "category_id", "tags", "is_pinned"],
                    "sortableAttributes": ["updated_at"],
                    "displayedAttributes": ["id", "title", "content_text", "tags", "updated_at"],
                },
            )
            if resp.status_code not in (200, 202):
                logger.warning("配置搜索索引失败 status=%s body=%s", resp.status_code, resp.text[:200])
                return False
            _index_ready = True
            return True

    # ── 写入 ──

    async def index_note(self, note: Note) -> bool:
        """整篇重建（幂等）：保存链路的高频调用不会产生重复文档"""
        if not settings.meili_configured:
            return False
        if not await self.ensure_index():
            return False
        client = self._get_client()
        resp = await client.post(
            f"/indexes/{settings.MEILI_INDEX}/documents",
            json=[self.build_document(note)],
            params={"primaryKey": "id"},
        )
        if resp.status_code not in (200, 202):
            logger.warning("笔记写入索引失败 note_id=%s status=%s", note.id, resp.status_code)
            return False
        return True

    async def index_notes(self, notes: list[Note]) -> bool:
        """批量 upsert（存量回填专用）：一次请求写入多条，显著降低往返开销"""
        if not notes or not settings.meili_configured:
            return False
        if not await self.ensure_index():
            return False
        resp = await self._get_client().post(
            f"/indexes/{settings.MEILI_INDEX}/documents",
            json=[self.build_document(n) for n in notes],
            params={"primaryKey": "id"},
        )
        if resp.status_code not in (200, 202):
            logger.warning("批量写入索引失败 count=%s status=%s", len(notes), resp.status_code)
            return False
        return True

    async def stats(self) -> int | None:
        """返回索引内文档数，供回填脚本校验；不可用时返回 None"""
        if not settings.meili_configured:
            return None
        try:
            resp = await self._get_client().get(f"/indexes/{settings.MEILI_INDEX}/stats")
            if resp.status_code != 200:
                return None
            return int(resp.json().get("numberOfDocuments", 0))
        except Exception:
            logger.exception("读取索引统计失败")
            return None

    @staticmethod
    def build_document(note: Note) -> dict:
        """组装索引文档；tags 在库中为 JSON 字符串，需反序列化为数组供 filter/facet 使用"""
        try:
            tags = json.loads(note.tags) if isinstance(note.tags, str) else list(note.tags or [])
        except (ValueError, TypeError):
            tags = []
        return {
            "id": note.id,
            "user_id": note.user_id,
            "category_id": note.category_id,
            "title": note.title,
            "content_text": strip_html(note.content),
            "tags": [t for t in tags if t],
            "is_pinned": note.is_pinned,
            "updated_at": int(note.updated_at.timestamp()) if note.updated_at else 0,
        }

    async def delete_note(self, note_id: int) -> bool:
        if not settings.meili_configured:
            return False
        if not await self.ensure_index():
            return False
        resp = await self._get_client().delete(
            f"/indexes/{settings.MEILI_INDEX}/documents/{note_id}"
        )
        if resp.status_code not in (200, 202, 204, 404):
            logger.warning("笔记删除索引失败 note_id=%s status=%s", note_id, resp.status_code)
            return False
        return True

    # ── 查询 ──

    async def search_note_ids(self, user_id: int, keyword: str, limit: int = 200) -> list[int] | None:
        """返回命中的笔记 ID（相关度降序）；服务不可用时返回 None 让调用方降级 LIKE"""
        if not settings.meili_configured:
            return None
        try:
            if not await self.ensure_index():
                return None
            resp = await self._get_client().post(
                f"/indexes/{settings.MEILI_INDEX}/search",
                json={
                    "q": keyword,
                    "limit": limit,
                    "filter": f"user_id = {int(user_id)}",
                    "attributesToRetrieve": ["id"],
                },
            )
            if resp.status_code != 200:
                logger.warning("搜索请求失败 status=%s body=%s", resp.status_code, resp.text[:200])
                return None
            return [int(hit["id"]) for hit in resp.json().get("hits", [])]
        except Exception:
            logger.exception("搜索服务不可用，降级为数据库 LIKE 查询 user_id=%s", user_id)
            return None

    async def health(self) -> bool:
        if not settings.meili_configured:
            return False
        try:
            resp = await self._get_client().get("/health")
            return resp.status_code == 200
        except Exception:
            return False


search_service = SearchService()


# ── BackgroundTasks 入口（与 RAG 索引同点位，失败只记日志）──

async def sync_note_to_search(user_id: int, note_id: int) -> None:
    """笔记保存后同步到搜索索引；使用独立会话（请求会话在响应后已关闭）"""
    if not settings.meili_configured:
        return
    async with SessionLocal() as db:
        result = await db.execute(
            select(Note).where(Note.id == note_id, Note.user_id == user_id)
        )
        note = result.scalar_one_or_none()
        if note is None:
            return
        try:
            await search_service.index_note(note)
        except Exception:
            logger.exception("笔记同步搜索索引失败 note_id=%s", note_id)


async def remove_note_from_search(note_id: int) -> None:
    """笔记删除后清理索引文档"""
    if not settings.meili_configured:
        return
    try:
        await search_service.delete_note(note_id)
    except Exception:
        logger.exception("笔记清理搜索索引失败 note_id=%s", note_id)
