"""笔记 Markdown 批量导入导出

导出：每篇笔记一个 .md（YAML frontmatter + 正文），打包为 zip；
      块笔记（content_format=json）把 TipTap 文档序列化为 Markdown，未识别节点回退纯文本。
导入：支持 .md / .markdown / .zip；frontmatter 读取 title/tags，标题回退首个 H1 或文件名。
"""
import io
import json
import re
import zipfile
from pathlib import Path

MAX_IMPORT_FILES = 200
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 20 * 1024 * 1024

_UNSAFE_FILENAME = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')
_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.S)
_MARKDOWN_SUFFIXES = (".md", ".markdown")


# ── 导出：笔记 → Markdown ─────────────────────────────


def _yaml_str(value: str) -> str:
    """JSON 双引号字符串同时是合法的 YAML 标量，避免手写转义"""
    return json.dumps(value, ensure_ascii=False)


def _safe_filename(title: str, note_id: int) -> str:
    base = _UNSAFE_FILENAME.sub("-", title).strip(" .")[:60] or "note"
    return f"{base}-{note_id}.md"


def _inline_markdown(node: dict) -> str:
    """行内节点（text / hardBreak / image）序列化"""
    node_type = node.get("type")
    if node_type == "text":
        text = node.get("text") or ""
        for mark in reversed(node.get("marks") or []):
            name = mark.get("type")
            if name == "bold":
                text = f"**{text}**"
            elif name == "italic":
                text = f"*{text}*"
            elif name == "strike":
                text = f"~~{text}~~"
            elif name == "code":
                text = f"`{text}`"
            elif name == "underline":
                text = f"<u>{text}</u>"
            elif name == "link":
                href = (mark.get("attrs") or {}).get("href") or ""
                if href:
                    text = f"[{text}]({href})"
        return text
    if node_type == "hardBreak":
        return "  \n"
    if node_type == "image":
        attrs = node.get("attrs") or {}
        src = attrs.get("src") or ""
        if not src:
            return ""
        title = attrs.get("title")
        suffix = f' "{title}"' if title else ""
        return f"![{attrs.get('alt') or ''}]({src}{suffix})"
    return "".join(_inline_markdown(child) for child in node.get("content") or [])


def _indent(text: str, prefix: str) -> str:
    return "\n".join(prefix + line if line else prefix.rstrip() for line in text.split("\n"))


def _render_list(node: dict, depth: int) -> str:
    ordered = node.get("type") == "orderedList"
    start = int((node.get("attrs") or {}).get("start") or 1)
    pad = "  " * depth
    lines: list[str] = []
    for idx, item in enumerate(node.get("content") or []):
        marker = f"{start + idx}. " if ordered else "- "
        rendered: list[str] = []
        for child in item.get("content") or []:
            child_type = child.get("type")
            if child_type in ("bulletList", "orderedList"):
                rendered.append(_render_list(child, depth + 1))
            elif child_type == "taskList":
                rendered.append(_render_task_list(child, depth + 1))
            else:
                rendered.append(_render_block(child, depth + 1))
        body = "\n".join(part for part in rendered if part.strip())
        if not body:
            lines.append(pad + marker.rstrip())
            continue
        body_lines = body.split("\n")
        lines.append(pad + marker + body_lines[0].strip())
        lines.extend(body_lines[1:])
    return "\n".join(lines)


def _render_task_list(node: dict, depth: int) -> str:
    pad = "  " * depth
    lines: list[str] = []
    for item in node.get("content") or []:
        checked = bool((item.get("attrs") or {}).get("checked"))
        marker = "- [x] " if checked else "- [ ] "
        first = True
        for child in item.get("content") or []:
            child_type = child.get("type")
            if child_type == "paragraph" and first:
                lines.append(pad + marker + _inline_markdown(child).strip())
                first = False
            elif child_type in ("bulletList", "orderedList"):
                lines.append(_render_list(child, depth + 1))
            elif child_type == "taskList":
                lines.append(_render_task_list(child, depth + 1))
            else:
                lines.append(_render_block(child, depth + 1))
    return "\n".join(lines)


def _render_table(node: dict) -> str:
    rows: list[list[str]] = []
    for row in node.get("content") or []:
        cells: list[str] = []
        for cell in row.get("content") or []:
            text = " ".join(
                _render_block(block, 0).strip()
                for block in cell.get("content") or []
                if block.get("type") != "table"
            ).strip()
            cells.append(text.replace("|", "\\|") or " ")
        rows.append(cells)
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    rows = [row + [" "] * (width - len(row)) for row in rows]
    lines = [
        "| " + " | ".join(rows[0]) + " |",
        "| " + " | ".join(["---"] * width) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
    return "\n".join(lines)


def _render_block(node: dict, depth: int = 0) -> str:
    node_type = node.get("type")
    pad = "  " * depth
    if node_type == "paragraph":
        text = _inline_markdown(node).strip()
        return pad + text if text else ""
    if node_type == "heading":
        level = min(max(int((node.get("attrs") or {}).get("level") or 1), 1), 6)
        return f"{'#' * level} {_inline_markdown(node).strip()}"
    if node_type in ("bulletList", "orderedList"):
        return _render_list(node, depth)
    if node_type == "taskList":
        return _render_task_list(node, depth)
    if node_type == "blockquote":
        inner = "\n\n".join(
            part for part in (_render_block(child, 0) for child in node.get("content") or []) if part.strip()
        )
        return _indent(inner, "> ")
    if node_type == "codeBlock":
        language = (node.get("attrs") or {}).get("language") or ""
        code = "".join(child.get("text") or "" for child in node.get("content") or [])
        return f"{pad}```{language}\n{code}\n```"
    if node_type == "horizontalRule":
        return "---"
    if node_type == "table":
        return _render_table(node)
    if node_type == "image":
        return _inline_markdown(node)
    inner = "\n".join(
        part for part in (_render_block(child, depth) for child in node.get("content") or []) if part.strip()
    )
    return inner


def tiptap_json_to_markdown(doc: dict) -> str:
    if not isinstance(doc, dict):
        return ""
    blocks = [
        rendered
        for rendered in (_render_block(node) for node in doc.get("content") or [])
        if rendered.strip()
    ]
    return "\n\n".join(blocks)


def _note_body(note) -> str:
    if note.content_format == "json" and note.content_json:
        try:
            return tiptap_json_to_markdown(json.loads(note.content_json))
        except (ValueError, TypeError):
            pass
    return note.content or ""


def note_to_markdown(note) -> str:
    tags: list[str] = []
    if note.tags:
        try:
            parsed = json.loads(note.tags)
            if isinstance(parsed, list):
                tags = [str(tag) for tag in parsed if str(tag).strip()]
        except (ValueError, TypeError):
            pass

    header = ["---", f"title: {_yaml_str(note.title)}"]
    if tags:
        header.append(f"tags: {json.dumps(tags, ensure_ascii=False)}")
    if note.created_at:
        header.append(f"created: {note.created_at.isoformat(timespec='seconds')}")
    if note.updated_at:
        header.append(f"updated: {note.updated_at.isoformat(timespec='seconds')}")
    header.append("---")
    return "\n".join(header) + "\n\n" + _note_body(note).rstrip() + "\n"


def notes_to_markdown_zip(notes) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for note in notes:
            archive.writestr(_safe_filename(note.title, note.id), note_to_markdown(note))
    return buffer.getvalue()


# ── 导入：Markdown → 笔记 ─────────────────────────────


def _decode_markdown(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("文件编码无法识别（仅支持 UTF-8 / GB18030）")


def _is_markdown_name(name: str) -> bool:
    pure = name.replace("\\", "/")
    if "__MACOSX/" in pure or Path(pure).name.startswith("."):
        return False
    return pure.lower().endswith(_MARKDOWN_SUFFIXES)


def extract_markdown_files(filename: str, raw: bytes) -> list[tuple[str, str]]:
    """把一次上传拆成 [(文件名, 文本)]；zip 只取 Markdown 条目并做体积/数量限制"""
    if filename.lower().endswith(".zip"):
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                infos = [
                    info
                    for info in archive.infolist()
                    if not info.is_dir() and _is_markdown_name(info.filename)
                ]
                if len(infos) > MAX_IMPORT_FILES:
                    raise ValueError(f"压缩包内 Markdown 超过 {MAX_IMPORT_FILES} 个")
                if sum(info.file_size for info in infos) > MAX_TOTAL_BYTES:
                    raise ValueError("压缩包解压后超过 20MB")
                return [
                    (Path(info.filename).name, _decode_markdown(archive.read(info)))
                    for info in infos
                ]
        except zipfile.BadZipFile as exc:
            raise ValueError("ZIP 文件已损坏") from exc
    if not _is_markdown_name(Path(filename).name):
        raise ValueError("仅支持 .md / .markdown / .zip 文件")
    return [(Path(filename).name, _decode_markdown(raw))]


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        if value[0] == '"':
            try:
                return json.loads(value)
            except ValueError:
                return value[1:-1]
        return value[1:-1]
    return value


def _parse_tags(value: str) -> list[str]:
    raw = value.strip()
    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
        except ValueError:
            parsed = None
        if isinstance(parsed, list):
            return [str(tag).strip() for tag in parsed if str(tag).strip()]
        raw = raw.strip("[]")
    return [tag.strip() for tag in raw.split(",") if tag.strip()]


def parse_markdown(filename: str, text: str) -> dict:
    """解析 frontmatter 与正文；标题优先级：frontmatter > 首个 H1 > 文件名"""
    title: str | None = None
    tags: list[str] = []
    body = text
    matched = _FRONTMATTER.match(text)
    if matched:
        body = text[matched.end():]
        for line in matched.group(1).splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip()
            if key == "title" and value:
                title = _unquote(value)
            elif key == "tags" and value:
                tags = _parse_tags(value)

    body = body.lstrip("\r\n")
    if not title:
        heading = re.search(r"^#\s+(.+?)\s*$", body, re.M)
        if heading:
            title = heading.group(1).strip()
            body = (body[:heading.start()] + body[heading.end():]).lstrip("\r\n")
    fallback = Path(filename).stem.strip() or "未命名笔记"
    title = (title or fallback).strip()[:255] or fallback[:255]

    content = body.rstrip()
    return {
        "title": title,
        "tags": tags,
        "content": content + "\n" if content else "",
    }
