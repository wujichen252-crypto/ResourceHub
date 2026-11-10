"""Markdown 批量导入导出回归测试：zip 结构、frontmatter、H1 回退、重复导入覆盖、非法文件跳过"""

import io
import json
import zipfile

from tests.conftest import register_user


def _create(client, auth, **kw):
    payload = {"title": "导出样例", "content": "正文内容"}
    payload.update(kw)
    resp = client.post("/api/notes", json=payload, headers=auth)
    assert resp.status_code == 201
    return resp.json()["data"]


def _upload(client, auth, files):
    return client.post("/api/notes/import/markdown", files=files, headers=auth)


def _zip_bytes(entries: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, text in entries.items():
            archive.writestr(name, text)
    return buffer.getvalue()


def test_export_markdown_zip_has_frontmatter_and_body(client, auth):
    _create(
        client, auth,
        title="Markdown 笔记", content="# 小标题\n正文", tags=["python", "导出"],
    )
    block_doc = {
        "type": "doc",
        "content": [
            {"type": "heading", "attrs": {"level": 2},
             "content": [{"type": "text", "text": "块标题"}]},
            {"type": "paragraph", "content": [
                {"type": "text", "text": "加粗", "marks": [{"type": "bold"}]},
                {"type": "text", "text": "与普通"},
            ]},
            {"type": "bulletList", "content": [
                {"type": "listItem", "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": "条目"}]}
                ]}
            ]},
        ],
    }
    _create(
        client, auth,
        title="块笔记", content="<p>HTML 快照</p>", content_json=block_doc,
    )

    resp = client.get("/api/notes/export/markdown", headers=auth)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert "attachment" in resp.headers["content-disposition"]

    with zipfile.ZipFile(io.BytesIO(resp.content)) as archive:
        names = archive.namelist()
        assert len(names) == 2
        assert all(name.endswith(".md") for name in names)
        files = {name: archive.read(name).decode("utf-8") for name in names}

    md_note = next(text for text in files.values() if "Markdown 笔记" in text)
    assert md_note.startswith("---\n")
    assert 'title: "Markdown 笔记"' in md_note
    assert 'tags: ["python", "导出"]' in md_note
    assert "正文" in md_note

    block_note = next(text for text in files.values() if "块笔记" in text)
    assert "## 块标题" in block_note
    assert "**加粗**与普通" in block_note
    assert "- 条目" in block_note
    assert "HTML 快照" not in block_note  # 块文档为权威，不导 HTML 快照


def test_export_json_contains_full_notes(client, auth):
    created = _create(client, auth, title="JSON 导出", content="全文内容", tags=["json"])

    resp = client.get("/api/notes/export/json", headers=auth)
    assert resp.status_code == 200
    items = json.loads(resp.content.decode("utf-8"))
    assert len(items) == 1
    item = items[0]
    assert item["id"] == created["id"]
    assert item["title"] == "JSON 导出"
    assert item["content"] == "全文内容"
    assert item["tags"] == ["json"]
    assert item["content_format"] == "markdown"


def test_export_only_current_user_notes(client, auth):
    _create(client, auth, title="alice 的笔记")
    bob = register_user(client, "bob")

    resp = client.get("/api/notes/export/markdown", headers=bob)
    with zipfile.ZipFile(io.BytesIO(resp.content)) as archive:
        assert archive.namelist() == []


def test_import_files_frontmatter_and_h1_fallback(client, auth):
    resp = _upload(
        client, auth,
        [
            ("files", ("one.md", "---\ntitle: \"带 Frontmatter\"\ntags: [\"a\", \"b\"]\n---\n\n正文一".encode(), "text/markdown")),
            ("files", ("two.markdown", "# H1 标题\n\n正文二".encode(), "text/markdown")),
        ],
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["created"] == 2
    assert data["replaced"] == 0
    assert data["skipped"] == []

    listed = client.get("/api/notes", params={"page_size": 100}, headers=auth).json()["data"]
    by_title = {item["title"]: item for item in listed["items"]}
    assert by_title["带 Frontmatter"]["tags"] == ["a", "b"]
    assert "H1 标题" in by_title

    detail = client.get(f"/api/notes/{by_title['H1 标题']['id']}", headers=auth).json()["data"]
    assert "正文二" in detail["content"]
    assert "# H1 标题" not in detail["content"]  # 首个 H1 被用作标题后从正文移除


def test_import_zip_and_reimport_replaces(client, auth):
    payload = _zip_bytes({
        "export/note-a.md": "---\ntitle: \"压缩包笔记\"\ntags: [\"zip\"]\n---\n\n第一版",
        "__MACOSX/._note-a.md": "垃圾",
        "export/.hidden.md": "# 隐藏",
        "export/skip.txt": "非 markdown",
    })
    first = _upload(client, auth, [("files", ("batch.zip", payload, "application/zip"))])
    assert first.status_code == 200
    assert first.json()["data"]["created"] == 1
    assert first.json()["data"]["total"] == 1

    second = _upload(
        client, auth,
        [("files", ("note-a.md", "---\ntitle: \"压缩包笔记\"\n---\n\n第二版".encode(), "text/markdown"))],
    )
    assert second.json()["data"]["replaced"] == 1
    assert second.json()["data"]["created"] == 0

    listed = client.get("/api/notes", params={"page_size": 100}, headers=auth).json()["data"]
    assert listed["total"] == 1
    note_id = listed["items"][0]["id"]
    detail = client.get(f"/api/notes/{note_id}", headers=auth).json()["data"]
    assert "第二版" in detail["content"]
    assert "第一版" not in detail["content"]


def test_import_skips_invalid_inputs(client, auth):
    resp = _upload(
        client, auth,
        [
            ("files", ("bad.txt", "纯文本".encode(), "text/plain")),
            ("files", ("broken.zip", b"not a zip", "application/zip")),
            ("files", ("empty.md", b"   \n\n", "text/markdown")),
        ],
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["created"] == 0
    assert data["replaced"] == 0
    assert data["total"] == 1  # 只有 empty.md 被识别为 Markdown 条目，但内容为空未入库
    reasons = {item["file"]: item["reason"] for item in data["skipped"]}
    assert reasons["bad.txt"] == "仅支持 .md / .markdown / .zip 文件"
    assert reasons["broken.zip"] == "ZIP 文件已损坏"
    assert reasons["empty.md"] == "内容为空"


def test_import_requires_auth(client):
    resp = client.post(
        "/api/notes/import/markdown",
        files=[("files", ("a.md", b"# x", "text/markdown"))],
    )
    assert resp.status_code == 401
