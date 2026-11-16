"""笔记双向链接服务

内容中的链接表示（唯一事实源是「标题」）：
- json 轨（TipTap）：text 节点携带 noteLink mark（attrs: title / noteId），chip 内文本即标题；
  未被自动补全转换的手输文本保留 `[[标题]]` 原样，同样参与提取。
- markdown 轨：纯文本 `[[标题]]`。

保存笔记时从权威内容提取全部引用标题，解析为同空间笔记后整表重建 note_links 行。
"""
import json
import re

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note
from app.models.note_link import NoteLink
from app.models.team import TeamMember

# [[标题]]：标题内不允许再出现方括号，避免嵌套歧义
WIKILINK_PATTERN = re.compile(r"\[\[([^\[\]]+)\]\]")

BACKLINK_LIMIT = 50


def _walk_tiptap(node, refs: list[tuple[str, int | None]]) -> None:
    """深度优先遍历 TipTap 文档，收集引用 (标题, 偏好的目标 ID)。

    noteLink 原子节点带 noteId（Logseq/SiYuan 的教训：ID 链接不受目标改名影响，
    优先按 ID 解析）；文本节点中手输的 [[标题]] 只有标题可用。
    """
    if isinstance(node, list):
        for child in node:
            _walk_tiptap(child, refs)
        return
    if not isinstance(node, dict):
        return

    if node.get("type") == "noteLink":
        attrs = node.get("attrs") or {}
        title = str(attrs.get("title") or "").strip()
        if title:
            note_id = attrs.get("noteId")
            refs.append((title, int(note_id) if note_id else None))

    if node.get("type") == "text" and node.get("text"):
        refs.extend(
            (match.strip(), None) for match in WIKILINK_PATTERN.findall(node["text"])
        )

    _walk_tiptap(node.get("content"), refs)


def extract_link_refs(note: Note) -> list[tuple[str, int | None]]:
    """从笔记权威内容提取全部引用（去重保序，忽略自引用与空标题）"""
    refs: list[tuple[str, int | None]] = []

    if note.content_format == "json" and note.content_json:
        try:
            doc = json.loads(note.content_json)
        except (ValueError, TypeError):
            doc = None
        if isinstance(doc, dict):
            _walk_tiptap(doc, refs)
    else:
        # markdown 轨：正文是权威
        refs.extend(
            (match.strip(), None)
            for match in WIKILINK_PATTERN.findall(note.content or "")
        )

    seen: set[str] = set()
    result: list[tuple[str, int | None]] = []
    for title, note_id in refs:
        title = title[:255]
        key = title.lower()
        if not title or key in seen or title == (note.title or ""):
            continue
        seen.add(key)
        result.append((title, note_id))
    return result


# 兼容旧命名：只关心标题列表的调用方
def extract_link_titles(note: Note) -> list[str]:
    return [title for title, _ in extract_link_refs(note)]


def _scope_filter(note: Note) -> list:
    """与来源笔记同空间的解析范围：团队笔记 → 同团队；个人笔记 → 作者的个人笔记"""
    if note.team_id is not None:
        return [Note.team_id == note.team_id]
    return [Note.user_id == note.user_id, Note.team_id.is_(None)]


async def _resolve_title_map(
    db: AsyncSession, note: Note, titles: list[str]
) -> dict[str, int]:
    """按标题批量解析目标笔记 ID；同名取最近更新的一篇。

    解析范围与来源笔记同空间：团队笔记 → 同团队笔记；个人笔记 → 作者的个人笔记。
    """
    if not titles:
        return {}
    result = await db.execute(
        select(Note.id, Note.title)
        .where(Note.title.in_(titles), *_scope_filter(note))
        .order_by(Note.updated_at.desc())
    )
    resolved: dict[str, int] = {}
    for note_id, title in result.all():
        # 查询按 updated_at 倒序，首个出现的即最新
        resolved.setdefault(title, note_id)
        resolved.setdefault(title.lower(), note_id)
    return resolved


async def _resolve_id_set(db: AsyncSession, note: Note, ids: set[int]) -> set[int]:
    """校验节点携带的 noteId 确实存在于同空间（防陈旧 ID / 跨空间引用）"""
    if not ids:
        return set()
    result = await db.execute(
        select(Note.id).where(Note.id.in_(ids), *_scope_filter(note))
    )
    return {row[0] for row in result.all()}


async def sync_note_links(db: AsyncSession, note: Note) -> None:
    """保存笔记后同步链接关系：整表删除重建，幂等且无需 diff。

    解析策略：节点自带 noteId 时优先按 ID 解析（对目标改名免疫）；
    否则按标题解析（同名取最近更新的一篇）。
    """
    refs = extract_link_refs(note)
    await db.execute(delete(NoteLink).where(NoteLink.source_note_id == note.id))
    if refs:
        valid_ids = await _resolve_id_set(
            db, note, {note_id for _, note_id in refs if note_id}
        )
        title_map = await _resolve_title_map(
            db, note, [title for title, note_id in refs if note_id not in valid_ids]
        )
        db.add_all(
            NoteLink(
                source_note_id=note.id,
                target_note_id=(
                    note_id if note_id in valid_ids
                    else title_map.get(title) or title_map.get(title.lower())
                ),
                target_title=title,
            )
            for title, note_id in refs
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
            {"id": source.id, "title": source.title, "updated_at": source.updated_at}
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
