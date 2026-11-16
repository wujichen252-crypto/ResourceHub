"""笔记双向链接服务

内容中的链接表示（唯一事实源是「标题」）：
- json 轨（TipTap）：noteLink 原子节点（attrs: title / noteId），chip 内文本即标题；
  未被自动补全转换的手输文本保留 `[[标题]]` 原样，同样参与提取。
- markdown 轨：纯文本 `[[标题]]`。

保存笔记时从权威内容提取全部引用（含引用处上下文片段），按 ID 优先解析为
来源作者可见的笔记（本人笔记或所在团队笔记）后整表重建 note_links 行。
"""
import json
import re

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note
from app.models.note_link import NoteLink
from app.models.team import Team, TeamMember

# [[标题]]：标题内不允许再出现方括号，避免嵌套歧义
WIKILINK_PATTERN = re.compile(r"\[\[([^\[\]]+)\]\]")

BACKLINK_LIMIT = 50
CONTEXT_MAX_CHARS = 200      # 引用上下文片段最大长度
COMPLETION_LIMIT = 8         # 链接补全最多候选数
GRAPH_NODE_LIMIT = 300       # 图谱节点上限（按最近更新截断）


class LinkRef:
    """一次引用：标题 + 偏好目标 ID + 引用处上下文片段"""

    __slots__ = ("title", "note_id", "context")

    def __init__(self, title: str, note_id: int | None, context: str | None) -> None:
        self.title = title
        self.note_id = note_id
        self.context = context


def _collect_inline_refs(node, out: list[tuple[str, int | None]]) -> None:
    """收集行内引用：noteLink 节点（带 ID）与文本节点中的 [[标题]]"""
    if isinstance(node, list):
        for child in node:
            _collect_inline_refs(child, out)
        return
    if not isinstance(node, dict):
        return
    if node.get("type") == "noteLink":
        attrs = node.get("attrs") or {}
        title = str(attrs.get("title") or "").strip()
        if title:
            note_id = attrs.get("noteId")
            out.append((title, int(note_id) if note_id else None))
    elif node.get("type") == "text" and node.get("text"):
        out.extend(
            (match.strip(), None) for match in WIKILINK_PATTERN.findall(node["text"])
        )
    _collect_inline_refs(node.get("content"), out)


def _block_text(node) -> str:
    """块内全部可见文本（noteLink 用标题占位），供上下文片段用"""
    parts: list[str] = []

    def walk(n) -> None:
        if isinstance(n, list):
            for child in n:
                walk(child)
            return
        if not isinstance(n, dict):
            return
        if n.get("type") == "text" and n.get("text"):
            parts.append(n["text"])
        elif n.get("type") == "noteLink":
            parts.append(str((n.get("attrs") or {}).get("title") or ""))
        walk(n.get("content"))

    walk(node)
    return "".join(parts)


def _block_has_ref(node) -> bool:
    found = False

    def walk(n) -> bool:
        nonlocal found
        if found:
            return True
        if isinstance(n, list):
            for child in n:
                walk(child)
            return found
        if not isinstance(n, dict):
            return False
        if n.get("type") == "noteLink":
            found = True
            return True
        if n.get("type") == "text" and WIKILINK_PATTERN.search(n.get("text") or ""):
            found = True
            return True
        walk(n.get("content"))
        return found

    return walk(node)


def _walk_blocks(node, out: list[LinkRef]) -> None:
    """深度优先遍历，遇到含引用的段落/标题块即提取引用 + 上下文，不再深入"""
    if isinstance(node, list):
        for child in node:
            _walk_blocks(child, out)
        return
    if not isinstance(node, dict):
        return
    if node.get("type") in ("paragraph", "heading"):
        if _block_has_ref(node):
            context = _block_text(node).strip()[:CONTEXT_MAX_CHARS] or None
            inline: list[tuple[str, int | None]] = []
            _collect_inline_refs(node, inline)
            for title, note_id in inline:
                out.append(LinkRef(title, note_id, context))
        return
    _walk_blocks(node.get("content"), out)


def extract_link_refs(note: Note) -> list[LinkRef]:
    """从笔记权威内容提取全部引用（同标题取首个引用处，忽略自引用与空标题）"""
    refs: list[LinkRef] = []

    if note.content_format == "json" and note.content_json:
        try:
            doc = json.loads(note.content_json)
        except (ValueError, TypeError):
            doc = None
        if isinstance(doc, dict):
            _walk_blocks(doc, refs)
    else:
        # markdown 轨：逐行提取，行文本即上下文
        for line in (note.content or "").splitlines():
            if not WIKILINK_PATTERN.search(line):
                continue
            context = line.strip()[:CONTEXT_MAX_CHARS] or None
            for match in WIKILINK_PATTERN.findall(line):
                refs.append(LinkRef(match.strip(), None, context))

    seen: set[str] = set()
    result: list[LinkRef] = []
    for ref in refs:
        title = ref.title[:255]
        key = title.lower()
        if not title or key in seen or title == (note.title or ""):
            continue
        seen.add(key)
        ref.title = title
        result.append(ref)
    return result


# 兼容旧命名：只关心标题列表的调用方
def extract_link_titles(note: Note) -> list[str]:
    return [ref.title for ref in extract_link_refs(note)]


async def _viewer_team_ids(db: AsyncSession, user_id: int) -> list[int]:
    result = await db.execute(
        select(TeamMember.team_id).where(TeamMember.user_id == user_id)
    )
    return [row[0] for row in result.all()]


async def _resolve_title_map(
    db: AsyncSession, note: Note, titles: list[str]
) -> dict[str, int]:
    """按标题批量解析目标笔记 ID；同名取最近更新的一篇。

    解析范围与来源笔记同空间：团队笔记 → 同团队笔记；个人笔记 → 作者的个人笔记。
    """
    if not titles:
        return {}
    scope = (
        [Note.team_id == note.team_id]
        if note.team_id is not None
        else [Note.user_id == note.user_id, Note.team_id.is_(None)]
    )
    result = await db.execute(
        select(Note.id, Note.title)
        .where(Note.title.in_(titles), *scope)
        .order_by(Note.updated_at.desc())
    )
    resolved: dict[str, int] = {}
    for note_id, title in result.all():
        # 查询按 updated_at 倒序，首个出现的即最新
        resolved.setdefault(title, note_id)
        resolved.setdefault(title.lower(), note_id)
    return resolved


async def _resolve_id_set(db: AsyncSession, note: Note, ids: set[int]) -> set[int]:
    """校验节点携带的 noteId 对来源作者可见（防陈旧 ID / 越权引用）。

    可见 = 目标是作者本人的笔记，或目标是作者所在团队的笔记。
    覆盖个人 ↔ 团队互链场景（补全候选来自团队空间时仍能正确解析）。
    """
    if not ids:
        return set()
    result = await db.execute(
        select(Note.id).where(
            Note.id.in_(ids),
            or_(
                Note.user_id == note.user_id,
                Note.team_id.in_(
                    select(TeamMember.team_id).where(TeamMember.user_id == note.user_id)
                ),
            ),
        )
    )
    return {row[0] for row in result.all()}


async def sync_note_links(db: AsyncSession, note: Note) -> None:
    """保存笔记后同步链接关系：整表删除重建，幂等且无需 diff。

    解析策略：节点自带 noteId 时优先按 ID 解析（对目标改名免疫，
    且要求目标对来源作者可见）；否则按标题在同空间解析（同名取最近更新的一篇）。
    """
    refs = extract_link_refs(note)
    await db.execute(delete(NoteLink).where(NoteLink.source_note_id == note.id))
    if refs:
        valid_ids = await _resolve_id_set(
            db, note, {ref.note_id for ref in refs if ref.note_id}
        )
        title_map = await _resolve_title_map(
            db, note, [ref.title for ref in refs if ref.note_id not in valid_ids]
        )
        db.add_all(
            NoteLink(
                source_note_id=note.id,
                target_note_id=(
                    ref.note_id if ref.note_id in valid_ids
                    else title_map.get(ref.title) or title_map.get(ref.title.lower())
                ),
                target_title=ref.title,
                context=ref.context,
            )
            for ref in refs
        )
    await db.commit()


async def refresh_target_titles(
    db: AsyncSession, note: Note, old_title: str
) -> None:
    """目标笔记改名后，刷新引用表中的标题快照。

    若某来源笔记已存在 (source, 新标题) 行（引用了另一篇同名笔记），跳过该行
    以避免违反唯一约束；旧行仍靠 target_note_id 维持反链，不影响正确性。
    """
    result = await db.execute(
        select(NoteLink).where(
            NoteLink.target_note_id == note.id, NoteLink.target_title == old_title
        )
    )
    rows = list(result.scalars().all())
    if not rows:
        return
    for row in rows:
        conflict = await db.scalar(
            select(NoteLink.id).where(
                NoteLink.source_note_id == row.source_note_id,
                NoteLink.target_title == note.title,
            )
        )
        if conflict:
            continue
        row.target_title = note.title
    await db.commit()


async def get_backlinks(db: AsyncSession, note: Note, viewer_id: int) -> list[dict]:
    """查询指向该笔记的反向链接（按来源笔记可见性过滤）

    来源可见 = 来源是查看者本人的笔记，或来源属于查看者所在的团队。
    """
    result = await db.execute(
        select(NoteLink, Note)
        .join(Note, NoteLink.source_note_id == Note.id)
        .where(NoteLink.target_note_id == note.id)
        .order_by(Note.updated_at.desc())
        .limit(BACKLINK_LIMIT)
    )
    rows = result.all()

    # 批量判断查看者对来源笔记团队空间的可见性，避免逐条 N+1
    team_ids = {source.team_id for _, source in rows if source.team_id is not None}
    visible_teams: set[int] = set()
    if team_ids:
        memberships = await db.execute(
            select(TeamMember.team_id).where(
                TeamMember.user_id == viewer_id, TeamMember.team_id.in_(team_ids)
            )
        )
        visible_teams = {team_id for (team_id,) in memberships.all()}

    backlinks: list[dict] = []
    for link, source in rows:
        if source.user_id != viewer_id and (
            source.team_id is None or source.team_id not in visible_teams
        ):
            continue
        backlinks.append(
            {
                "id": source.id,
                "title": source.title,
                "updated_at": source.updated_at,
                "context": link.context,
            }
        )
    return backlinks


async def resolve_note_title(
    db: AsyncSession, title: str, viewer_id: int, team_id: int | None
) -> Note | None:
    """按标题解析笔记（点击链接跳转用）：个人空间 → 指定团队空间"""
    scope = (
        [Note.team_id == team_id]
        if team_id is not None
        else [Note.user_id == viewer_id, Note.team_id.is_(None)]
    )
    return await db.scalar(
        select(Note).where(Note.title == title, *scope).order_by(Note.updated_at.desc())
    )


async def get_completion_candidates(
    db: AsyncSession, user_id: int, query: str, limit: int = COMPLETION_LIMIT
) -> list[dict]:
    """链接补全候选：个人笔记 + 所在团队空间的笔记，带团队名标记"""
    team_ids = await _viewer_team_ids(db, user_id)
    # 注意：个人笔记必须 user_id 与 team_id 同时约束（AND），
    # 否则 or_ 会把其他用户 team_id 为空的笔记全部泄露出去
    scope: list = [and_(Note.user_id == user_id, Note.team_id.is_(None))]
    if team_ids:
        scope.append(Note.team_id.in_(team_ids))

    stmt = select(Note.id, Note.title, Note.team_id).where(or_(*scope))
    query = query.strip()
    if query:
        stmt = stmt.where(Note.title.ilike(f"%{query}%"))
    rows = (await db.execute(
        stmt.order_by(Note.updated_at.desc()).limit(limit)
    )).all()

    team_names: dict[int, str] = {}
    ref_team_ids = {row[2] for row in rows if row[2] is not None}
    if ref_team_ids:
        team_rows = await db.execute(
            select(Team.id, Team.name).where(Team.id.in_(ref_team_ids))
        )
        team_names = dict(team_rows.all())

    return [
        {
            "id": row[0],
            "title": row[1],
            "team_id": row[2],
            "team_name": team_names.get(row[2]) if row[2] is not None else None,
        }
        for row in rows
    ]


async def get_graph_data(db: AsyncSession, user_id: int) -> dict:
    """知识图谱数据：可见笔记为节点，note_links 为连线（两端均在可见范围内）"""
    team_ids = await _viewer_team_ids(db, user_id)
    # 同 completion：个人笔记用 AND 约束，防止 or_ 泄露其他用户的个人笔记
    scope: list = [and_(Note.user_id == user_id, Note.team_id.is_(None))]
    if team_ids:
        scope.append(Note.team_id.in_(team_ids))

    node_rows = (await db.execute(
        select(Note.id, Note.title, Note.team_id)
        .where(or_(*scope))
        .order_by(Note.updated_at.desc())
        .limit(GRAPH_NODE_LIMIT)
    )).all()
    node_ids = {row[0] for row in node_rows}

    team_names: dict[int, str] = {}
    ref_team_ids = {row[2] for row in node_rows if row[2] is not None}
    if ref_team_ids:
        team_rows = await db.execute(
            select(Team.id, Team.name).where(Team.id.in_(ref_team_ids))
        )
        team_names = dict(team_rows.all())

    link_rows = (await db.execute(
        select(NoteLink.source_note_id, NoteLink.target_note_id)
        .where(
            NoteLink.target_note_id.isnot(None),
            NoteLink.source_note_id.in_(node_ids),
            NoteLink.target_note_id.in_(node_ids),
        )
        .distinct()
    )).all()

    return {
        "nodes": [
            {
                "id": row[0],
                "title": row[1],
                "team_id": row[2],
                "team_name": team_names.get(row[2]) if row[2] is not None else None,
            }
            for row in node_rows
        ],
        "links": [
            {"source": row[0], "target": row[1]} for row in link_rows
        ],
    }
