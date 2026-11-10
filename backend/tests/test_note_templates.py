"""笔记模板接口回归测试 — CRUD、双轨内容、块 id 补齐、用户隔离"""

from tests.conftest import register_user


def _template(client, auth, **kw):
    payload = {"name": "周报", "content": "# 本周", "tags": ["work"]}
    payload.update(kw)
    return client.post("/api/note-templates", json=payload, headers=auth)


def test_create_and_list_markdown_template(client, auth):
    resp = _template(client, auth, content="# 本周\n- 完成 A")
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["name"] == "周报"
    assert data["content"] == "# 本周\n- 完成 A"
    assert data["content_format"] == "markdown"
    assert data["content_json"] is None
    assert data["tags"] == ["work"]

    items = client.get("/api/note-templates", headers=auth).json()["data"]["items"]
    assert [item["id"] for item in items] == [data["id"]]


def test_create_json_template_backfills_block_ids(client, auth):
    block_doc = {
        "type": "doc",
        "content": [
            {"type": "heading", "attrs": {"level": 1, "id": "keepme"}},
            {"type": "paragraph"},
        ],
    }
    resp = _template(client, auth, content="<h1>本周</h1>", content_json=block_doc)
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["content_format"] == "json"
    blocks = data["content_json"]["content"]
    assert blocks[0]["attrs"]["id"] == "keepme"
    assert len(blocks[1]["attrs"]["id"]) == 12


def test_update_switches_back_to_markdown(client, auth):
    created = _template(
        client, auth, content_json={"type": "doc", "content": [{"type": "paragraph"}]}
    ).json()["data"]

    resp = client.put(
        f"/api/note-templates/{created['id']}",
        json={"name": "月报", "content": "# 月报", "tags": ["work", "monthly"]},
        headers=auth,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["name"] == "月报"
    assert data["tags"] == ["work", "monthly"]
    assert data["content_format"] == "markdown"
    assert data["content_json"] is None


def test_delete_template(client, auth):
    created = _template(client, auth).json()["data"]

    assert client.delete(f"/api/note-templates/{created['id']}", headers=auth).status_code == 200
    missing = client.get("/api/note-templates", headers=auth).json()["data"]["items"]
    assert missing == []
    assert client.put(
        f"/api/note-templates/{created['id']}", json={"name": "x"}, headers=auth
    ).status_code == 404


def test_user_isolation(client, auth):
    created = _template(client, auth).json()["data"]
    bob_auth = register_user(client, "bob")

    assert client.get("/api/note-templates", headers=bob_auth).json()["data"]["items"] == []
    assert client.put(
        f"/api/note-templates/{created['id']}", json={"name": "hijack"}, headers=bob_auth
    ).status_code == 404
    assert client.delete(
        f"/api/note-templates/{created['id']}", headers=bob_auth
    ).status_code == 404
    assert client.get("/api/note-templates", headers=auth).json()["data"]["items"][0]["name"] == "周报"
