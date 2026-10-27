"""Agent 工具注册表

工具分两类：
- 只读工具：检索、读笔记、列分类、搜提示词，可直接执行
- 写工具：新建/更新笔记，必须经用户确认（人在环），由 AgentService 拦截

所有工具都按 user_id 隔离，模型无法越权访问其他用户数据。
"""

import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.note import Note
from app.models.prompt import Prompt
from app.services.ai.retrieval import retrieve

logger = logging.getLogger(__name__)

MAX_TOOL_RESULT_CHARS = 4000


@dataclass(slots=True)
class ToolContext:
    """工具执行上下文：绑定当前用户与数据库会话"""

    db: AsyncSession
    user_id: int


@dataclass(slots=True)
class Tool:
    """工具定义"""

    name: str
    description: str
    parameters: dict[str, Any]
    write: bool
    handler: Callable[[ToolContext, dict[str, Any]], Awaitable[str]]


class ToolRegistry:
    """工具注册与执行入口"""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def specs(self) -> list[dict[str, Any]]:
        """转换为 OpenAI Function Calling 的工具描述"""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]

    def is_write(self, name: str) -> bool:
        """判断是否写工具"""
        tool = self._tools.get(name)
        return bool(tool and tool.write)

    async def execute(self, name: str, arguments: str | dict[str, Any], ctx: ToolContext) -> str:
        """执行工具并返回文本结果，错误也以文本返回供模型自我修正"""
        tool = self._tools.get(name)
        if tool is None:
            return json.dumps({"success": False, "error": f"未知工具：{name}"}, ensure_ascii=False)

        payload = self._parse_arguments(arguments)
        if payload is None:
            return json.dumps(
                {"success": False, "error": "参数不是合法 JSON 对象"}, ensure_ascii=False
            )

        try:
            result = await tool.handler(ctx, payload)
        except Exception as exc:  # 工具异常交还模型处理，不中断整个 Agent
            logger.exception("工具 %s 执行失败", name)
            return json.dumps({"success": False, "error": str(exc)[:200]}, ensure_ascii=False)
        return result[:MAX_TOOL_RESULT_CHARS]

    @staticmethod
    def _parse_arguments(arguments: str | dict[str, Any]) -> dict[str, Any] | None:
        if isinstance(arguments, dict):
            return arguments
        try:
            value = json.loads(arguments or "{}")
        except json.JSONDecodeError:
            return None
        return value if isinstance(value, dict) else None


async def _search_notes(ctx: ToolContext, args: dict[str, Any]) -> str:
    """语义 + 关键词混合检索笔记"""
    query = str(args.get("query", "")).strip()
    if not query:
        return json.dumps({"success": False, "error": "query 不能为空"}, ensure_ascii=False)
    top_k = min(int(args.get("top_k", 5)), 10)
    hits = await retrieve(ctx.db, ctx.user_id, query, top_k)
    return json.dumps(
        {
            "success": True,
            "results": [
                {
                    "note_id": hit.note_id,
                    "title": hit.note_title,
                    "snippet": hit.content[:300],
                    "score": hit.score,
                }
                for hit in hits
            ],
        },
        ensure_ascii=False,
    )


async def _read_note(ctx: ToolContext, args: dict[str, Any]) -> str:
    """读取笔记全文"""
    note_id = int(args.get("note_id", 0))
    result = await ctx.db.execute(
        select(Note).where(Note.id == note_id, Note.user_id == ctx.user_id)
    )
    note = result.scalar_one_or_none()
    if note is None:
        return json.dumps({"success": False, "error": "笔记不存在"}, ensure_ascii=False)
    return json.dumps(
        {"success": True, "id": note.id, "title": note.title, "content": note.content or ""},
        ensure_ascii=False,
    )


async def _list_categories(ctx: ToolContext, _args: dict[str, Any]) -> str:
    """列出当前用户的分类树"""
    result = await ctx.db.execute(
        select(Category).where(Category.user_id == ctx.user_id).order_by(Category.id)
    )
    categories = result.scalars().all()
    return json.dumps(
        {
            "success": True,
            "categories": [
                {"id": item.id, "name": item.name, "type": item.type, "parent_id": item.parent_id}
                for item in categories
            ],
        },
        ensure_ascii=False,
    )


async def _search_prompts(ctx: ToolContext, args: dict[str, Any]) -> str:
    """按关键词搜索提示词库"""
    keyword = str(args.get("keyword", "")).strip()
    query = select(Prompt).where(Prompt.user_id == ctx.user_id)
    if keyword:
        query = query.where(Prompt.title.ilike(f"%{keyword}%"))
    result = await ctx.db.execute(query.order_by(Prompt.updated_at.desc()).limit(10))
    prompts = result.scalars().all()
    return json.dumps(
        {
            "success": True,
            "prompts": [
                {"id": item.id, "title": item.title, "description": item.description}
                for item in prompts
            ],
        },
        ensure_ascii=False,
    )


async def _create_note(ctx: ToolContext, args: dict[str, Any]) -> str:
    """新建笔记（写操作，需用户确认）"""
    title = str(args.get("title", "")).strip()
    content = str(args.get("content", "")).strip()
    if not title:
        return json.dumps({"success": False, "error": "title 不能为空"}, ensure_ascii=False)
    category_id = args.get("category_id")
    note = Note(
        user_id=ctx.user_id,
        title=title[:255],
        content=content,
        category_id=int(category_id) if category_id else None,
    )
    ctx.db.add(note)
    await ctx.db.flush()
    return json.dumps(
        {"success": True, "note_id": note.id, "title": note.title}, ensure_ascii=False
    )


async def _update_note(ctx: ToolContext, args: dict[str, Any]) -> str:
    """更新笔记标题或正文（写操作，需用户确认）"""
    note_id = int(args.get("note_id", 0))
    result = await ctx.db.execute(
        select(Note).where(Note.id == note_id, Note.user_id == ctx.user_id)
    )
    note = result.scalar_one_or_none()
    if note is None:
        return json.dumps({"success": False, "error": "笔记不存在"}, ensure_ascii=False)
    if args.get("title"):
        note.title = str(args["title"])[:255]
    if args.get("content") is not None:
        note.content = str(args["content"])
    await ctx.db.flush()
    return json.dumps({"success": True, "note_id": note.id}, ensure_ascii=False)


def build_default_registry() -> ToolRegistry:
    """注册内置工具集"""
    registry = ToolRegistry()
    registry.register(
        Tool(
            name="search_notes",
            description="在当前用户的笔记中做混合检索，返回相关片段。回答知识类问题前应先调用。",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索关键词或问题"},
                    "top_k": {"type": "integer", "description": "返回片段数，默认 5", "minimum": 1, "maximum": 10},
                },
                "required": ["query"],
            },
            write=False,
            handler=_search_notes,
        )
    )
    registry.register(
        Tool(
            name="read_note",
            description="按 ID 读取一篇笔记的完整内容。",
            parameters={
                "type": "object",
                "properties": {"note_id": {"type": "integer", "description": "笔记 ID"}},
                "required": ["note_id"],
            },
            write=False,
            handler=_read_note,
        )
    )
    registry.register(
        Tool(
            name="list_categories",
            description="列出用户的笔记/提示词分类，用于确定新建内容归属。",
            parameters={"type": "object", "properties": {}},
            write=False,
            handler=_list_categories,
        )
    )
    registry.register(
        Tool(
            name="search_prompts",
            description="按关键词搜索用户的提示词库。",
            parameters={
                "type": "object",
                "properties": {"keyword": {"type": "string", "description": "标题关键词"}},
            },
            write=False,
            handler=_search_prompts,
        )
    )
    registry.register(
        Tool(
            name="create_note",
            description="新建一篇笔记。属于写操作，需要用户确认后才会真正执行。",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "笔记标题"},
                    "content": {"type": "string", "description": "Markdown 正文"},
                    "category_id": {"type": "integer", "description": "可选分类 ID"},
                },
                "required": ["title", "content"],
            },
            write=True,
            handler=_create_note,
        )
    )
    registry.register(
        Tool(
            name="update_note",
            description="更新已有笔记的标题或正文。属于写操作，需要用户确认。",
            parameters={
                "type": "object",
                "properties": {
                    "note_id": {"type": "integer", "description": "笔记 ID"},
                    "title": {"type": "string", "description": "新标题"},
                    "content": {"type": "string", "description": "新正文"},
                },
                "required": ["note_id"],
            },
            write=True,
            handler=_update_note,
        )
    )
    return registry


TOOL_REGISTRY = build_default_registry()
