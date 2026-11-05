"""笔记模块回归测试 — 锁定列表/详情序列化契约（preview 剥 HTML、tags JSON 解码、category_name 富化）"""

NOTE_FIELDS = {"id", "title", "content_preview", "category_id", "category_name",
               "tags", "is_pinned", "visibility", "created_at", "updated_at"}
DETAIL_FIELDS = {"id", "title", "content", "content_format", "content_json",
                 "category_id", "category_name",
                 "tags", "is_pinned", "visibility", "source_username",
                 "created_at", "updated_at"}


def _create_note(client, auth, category_id=None, **kw):
    payload = {"title": "FastAPI 入门", "content": "# 标题\n正文",
               "category_id": category_id, "tags": ["python", "fastapi"]}
    payload.update(kw)
    resp = client.post("/api/notes", json=payload, headers=auth)
    assert resp.status_code == 201
    return resp.json()["data"]


def test_create_note_detail_contract(client, auth):
    data = _create_note(client, auth)
    assert set(data) == DETAIL_FIELDS
    assert data["tags"] == ["python", "fastapi"]
    assert data["is_pinned"] is False
    assert data["category_name"] is None


def test_list_note_contract_strips_html_in_preview(client, auth):
    _create_note(client, auth, content="<p>Hello<br>World</p>")
    resp = client.get("/api/notes", headers=auth)
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert {"items", "total", "page", "page_size"} <= set(body)
    item = body["items"][0]
    assert set(item) == NOTE_FIELDS
    assert "<" not in item["content_preview"]  # HTML 已剥离
    assert "\n" not in item["content_preview"]
    assert "content" not in item  # 列表不返回全文


def test_get_update_delete_flow(client, auth):
    created = _create_note(client, auth)
    nid = created["id"]

    got = client.get(f"/api/notes/{nid}", headers=auth)
    assert set(got.json()["data"]) == DETAIL_FIELDS

    updated = client.put(
        f"/api/notes/{nid}",
        json={"title": "改名", "tags": ["go"]},
        headers=auth,
    )
    assert updated.json()["data"]["title"] == "改名"
    assert updated.json()["data"]["tags"] == ["go"]

    deleted = client.delete(f"/api/notes/{nid}", headers=auth)
    assert deleted.status_code == 200
    missing = client.get(f"/api/notes/{nid}", headers=auth)
    assert missing.status_code == 404
    assert missing.json()["msg"] == "笔记不存在"


def test_toggle_pin(client, auth):
    created = _create_note(client, auth)
    resp = client.put(f"/api/notes/{created['id']}/pin", headers=auth)
    assert resp.json()["data"] == {"id": created["id"], "is_pinned": True}


def test_search_filter(client, auth):
    _create_note(client, auth, title="Redis 缓存", content="穿透与雪崩")
    _create_note(client, auth, title="Kafka 消息", content="分区策略")
    resp = client.get("/api/notes", params={"search": "Redis"}, headers=auth)
    body = resp.json()["data"]
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Redis 缓存"


def test_tag_filter(client, auth):
    _create_note(client, auth, title="A", tags=["solo"])
    _create_note(client, auth, title="B", tags=["other"])
    resp = client.get("/api/notes", params={"tag": "solo"}, headers=auth)
    body = resp.json()["data"]
    assert body["total"] == 1


def test_category_name_enrichment(client, auth):
    cat = client.post(
        "/api/categories", json={"name": "技术", "type": "note"}, headers=auth
    ).json()["data"]
    created = _create_note(client, auth, category_id=cat["id"])
    detail = client.get(f"/api/notes/{created['id']}", headers=auth)
    assert detail.json()["data"]["category_name"] == "技术"


def test_import_replaces_same_title_in_same_category(client, auth):
    r1 = client.post(
        "/api/notes/import",
        json={"title": "同题", "content": "第一版", "category_id": None, "tags": []},
        headers=auth,
    )
    r2 = client.post(
        "/api/notes/import",
        json={"title": "同题", "content": "第二版", "category_id": None, "tags": []},
        headers=auth,
    )
    assert r1.json()["msg"] == "导入笔记成功"
    assert r2.json()["msg"] == "已替换同目录同名笔记"
    assert r2.json()["data"]["id"] == r1.json()["data"]["id"]
    assert r2.json()["data"]["content"] == "第二版"


def test_user_isolation(client, auth):
    """B 用户不可见 A 用户的笔记（user_id 数据隔离契约）"""
    from conftest import register_user

    created = _create_note(client, auth)
    bob = register_user(client, "bob2")
    resp = client.get(f"/api/notes/{created['id']}", headers=bob)
    assert resp.status_code == 404


# ── 存储双轨（content_format / content_json）──

BLOCK_JSON = {
    "type": "doc",
    "content": [
        {"type": "heading", "attrs": {"level": 1}},
        {"type": "paragraph", "attrs": {}, "content": [{"type": "text", "text": "块内容"}]},
    ],
}


def test_create_note_json_track_fills_block_ids(client, auth):
    """JSON 轨创建：content_format=json、顶层块自动补稳定 id、HTML 快照保留在 content"""
    resp = client.post(
        "/api/notes",
        json={"title": "块笔记", "content": "<h1>标题</h1><p>块内容</p>",
              "content_json": BLOCK_JSON, "tags": []},
        headers=auth,
    )
    data = resp.json()["data"]
    assert data["content_format"] == "json"
    assert data["content"] == "<h1>标题</h1><p>块内容</p>"
    blocks = data["content_json"]["content"]
    assert all(b["attrs"].get("id") for b in blocks)  # 顶层块均有 id
    # 已有 id 保留、缺失 id 补齐后不被重写
    fid = blocks[0]["attrs"]["id"]
    again = client.get(f"/api/notes/{data['id']}", headers=auth).json()["data"]
    assert again["content_json"]["content"][0]["attrs"]["id"] == fid


def test_create_note_markdown_track_backward_compatible(client, auth):
    """不传 content_json 时保持 markdown 单轨（旧客户端 / MD 导入零回归）"""
    created = _create_note(client, auth, content="# 标题\n正文")
    assert created["content_format"] == "markdown"
    assert created["content_json"] is None
    assert created["content"] == "# 标题\n正文"


def test_update_note_switch_to_json_track(client, auth):
    """旧 markdown 笔记经块编辑器保存后升级为 json 轨，content 同步为 HTML 快照"""
    created = _create_note(client, auth, content="旧 markdown")
    nid = created["id"]
    updated = client.put(
        f"/api/notes/{nid}",
        json={"content": "<p>新块内容</p>", "content_json": BLOCK_JSON},
        headers=auth,
    )
    data = updated.json()["data"]
    assert data["content_format"] == "json"
    assert data["content"] == "<p>新块内容</p>"


def test_update_note_partial_fields_keep_json_track(client, auth):
    """只改标题 / 置顶等字段时，双轨字段保持不变（exclude_unset 语义）"""
    created = client.post(
        "/api/notes",
        json={"title": "T", "content": "<p>x</p>", "content_json": BLOCK_JSON, "tags": []},
        headers=auth,
    ).json()["data"]
    updated = client.put(
        f"/api/notes/{created['id']}", json={"title": "T2"}, headers=auth
    ).json()["data"]
    assert updated["title"] == "T2"
    assert updated["content_format"] == "json"
    assert updated["content_json"]["content"][0]["type"] == "heading"


def test_json_track_preview_and_search_fall_back_to_content(client, auth):
    """json 轨笔记的列表预览与搜索走 content HTML 快照，不受双轨影响"""
    client.post(
        "/api/notes",
        json={"title": "检索", "content": "<p>独特检索词qwerty</p>", "content_json": BLOCK_JSON, "tags": []},
        headers=auth,
    )
    listing = client.get("/api/notes", headers=auth).json()["data"]["items"][0]
    assert "独特检索词qwerty" in listing["content_preview"]
    found = client.get("/api/notes", params={"search": "qwerty"}, headers=auth)
    assert found.json()["data"]["total"] == 1
