"""笔记批量操作回归测试 — 移动 / 追加标签 / 删除 / 归属校验"""

from tests.conftest import register_user


def _note(client, auth, title="笔记", tags=None, category_id=None):
    resp = client.post(
        "/api/notes",
        json={"title": title, "content": "正文", "category_id": category_id, "tags": tags or []},
        headers=auth,
    )
    assert resp.status_code == 201
    return resp.json()["data"]


def _category(client, auth, name="目录"):
    resp = client.post(
        "/api/categories", json={"name": name, "type": "note", "parent_id": None}, headers=auth
    )
    assert resp.status_code == 201
    return resp.json()["data"]


def _batch(client, auth, ids, action, **extra):
    return client.post(
        "/api/notes/batch", json={"ids": ids, "action": action, **extra}, headers=auth
    )


def test_batch_move_into_and_out_of_category(client, auth):
    cat = _category(client, auth, "资料")
    a = _note(client, auth, "A")
    b = _note(client, auth, "B")

    resp = _batch(client, auth, [a["id"], b["id"]], "move", category_id=cat["id"])
    assert resp.status_code == 200
    assert resp.json()["data"]["affected"] == 2
    assert client.get(f"/api/notes/{a['id']}", headers=auth).json()["data"]["category_id"] == cat["id"]

    resp = _batch(client, auth, [a["id"], b["id"]], "move", category_id=None)
    assert resp.json()["data"]["affected"] == 2
    assert client.get(f"/api/notes/{a['id']}", headers=auth).json()["data"]["category_id"] is None


def test_batch_tag_appends_and_dedupes(client, auth):
    note = _note(client, auth, "A", ["keep"])

    first = _batch(client, auth, [note["id"]], "tag", tags=["keep", "new"])
    assert first.status_code == 200
    detail = client.get(f"/api/notes/{note['id']}", headers=auth).json()["data"]
    assert detail["tags"] == ["keep", "new"]

    _batch(client, auth, [note["id"]], "tag", tags=["new", "extra"])
    detail = client.get(f"/api/notes/{note['id']}", headers=auth).json()["data"]
    assert detail["tags"] == ["keep", "new", "extra"]


def test_batch_delete(client, auth):
    a = _note(client, auth, "A")
    b = _note(client, auth, "B")

    resp = _batch(client, auth, [a["id"], b["id"]], "delete")
    assert resp.status_code == 200
    assert resp.json()["data"]["affected"] == 2
    assert client.get(f"/api/notes/{a['id']}", headers=auth).status_code == 404
    assert client.get(f"/api/notes/{b['id']}", headers=auth).status_code == 404
    assert client.get("/api/notes", headers=auth).json()["data"]["total"] == 0


def test_batch_only_touches_own_notes(client, auth):
    bob_auth = register_user(client, "bob")
    bob_note = _note(client, bob_auth, "B", ["secret"])

    resp = _batch(client, auth, [bob_note["id"]], "delete")
    assert resp.status_code == 200
    assert resp.json()["data"]["affected"] == 0
    assert client.get(f"/api/notes/{bob_note['id']}", headers=bob_auth).status_code == 200


def test_batch_move_rejects_foreign_category(client, auth):
    bob_auth = register_user(client, "bob")
    bob_cat = _category(client, bob_auth, "Bob目录")
    note = _note(client, auth, "A")

    resp = _batch(client, auth, [note["id"]], "move", category_id=bob_cat["id"])
    assert resp.status_code == 404
    assert resp.json()["msg"] == "目录不存在"
    assert client.get(f"/api/notes/{note['id']}", headers=auth).json()["data"]["category_id"] is None


def test_batch_tag_requires_tags(client, auth):
    note = _note(client, auth, "A")

    resp = _batch(client, auth, [note["id"]], "tag", tags=["  "])
    assert resp.status_code == 400
    assert resp.json()["msg"] == "请选择要添加的标签"


def test_batch_rejects_empty_ids(client, auth):
    resp = _batch(client, auth, [], "delete")
    assert resp.status_code == 422
