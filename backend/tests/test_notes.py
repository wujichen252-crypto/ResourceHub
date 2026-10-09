"""笔记模块回归测试 — 锁定列表/详情序列化契约（preview 剥 HTML、tags JSON 解码、category_name 富化）"""

NOTE_FIELDS = {"id", "title", "content_preview", "category_id", "category_name",
               "tags", "is_pinned", "created_at", "updated_at"}
DETAIL_FIELDS = {"id", "title", "content", "category_id", "category_name",
                 "tags", "is_pinned", "created_at", "updated_at"}


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
