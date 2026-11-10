"""标签管理接口回归测试 — 计数、重命名、合并去重、清理、双 scope 与用户隔离"""

from tests.conftest import register_user


def _note(client, auth, title="笔记", tags=None):
    resp = client.post(
        "/api/notes",
        json={"title": title, "content": "正文", "category_id": None, "tags": tags or []},
        headers=auth,
    )
    assert resp.status_code == 201
    return resp.json()["data"]


def _prompt(client, auth, title="提示词", tags=None):
    resp = client.post(
        "/api/prompts",
        json={
            "title": title,
            "description": "",
            "content": "hi",
            "category_id": None,
            "variables": [],
            "tags": tags or [],
        },
        headers=auth,
    )
    assert resp.status_code == 201
    return resp.json()["data"]


def _tag_map(client, auth, scope="note"):
    resp = client.get("/api/tags", params={"scope": scope}, headers=auth)
    assert resp.status_code == 200
    return {item["name"]: item["count"] for item in resp.json()["data"]["items"]}


def _detail(client, auth, note_id):
    return client.get(f"/api/notes/{note_id}", headers=auth).json()["data"]


def test_list_counts_within_scope(client, auth):
    _note(client, auth, "A", ["python", "ai"])
    _note(client, auth, "B", ["python"])
    _prompt(client, auth, "P", ["python", "prompt-only"])

    assert _tag_map(client, auth, "note") == {"python": 2, "ai": 1}
    assert _tag_map(client, auth, "prompt") == {"python": 1, "prompt-only": 1}


def test_rename_updates_rows_and_dedupes(client, auth):
    first = _note(client, auth, "A", ["a", "b"])
    second = _note(client, auth, "B", ["b"])

    resp = client.post(
        "/api/tags/rename",
        json={"scope": "note", "old_name": "a", "new_name": "b"},
        headers=auth,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["updated"] == 1

    # 第一篇本来就有 b，重命名后必须去重而不是出现 ["b", "b"]；第二篇无 a 不受影响
    assert _detail(client, auth, first["id"])["tags"] == ["b"]
    assert _detail(client, auth, second["id"])["tags"] == ["b"]
    assert _tag_map(client, auth, "note") == {"b": 2}


def test_merge_and_delete(client, auth):
    first = _note(client, auth, "A", ["a", "b", "c"])
    second = _note(client, auth, "B", ["c", "d"])

    merged = client.post(
        "/api/tags/merge",
        json={"scope": "note", "sources": ["a", "b"], "target": "c"},
        headers=auth,
    )
    assert merged.status_code == 200
    assert merged.json()["data"]["updated"] == 1
    assert _detail(client, auth, first["id"])["tags"] == ["c"]

    deleted = client.request(
        "DELETE", "/api/tags", params={"scope": "note", "name": "c"}, headers=auth
    )
    assert deleted.status_code == 200
    assert deleted.json()["data"]["updated"] == 2
    assert _detail(client, auth, first["id"])["tags"] == []
    assert _detail(client, auth, second["id"])["tags"] == ["d"]
    assert _tag_map(client, auth, "note") == {"d": 1}


def test_scope_isolation(client, auth):
    note = _note(client, auth, "A", ["shared"])
    _prompt(client, auth, "P", ["shared"])

    resp = client.post(
        "/api/tags/rename",
        json={"scope": "prompt", "old_name": "shared", "new_name": "renamed"},
        headers=auth,
    )
    assert resp.json()["data"]["updated"] == 1
    assert _detail(client, auth, note["id"])["tags"] == ["shared"]
    assert _tag_map(client, auth, "prompt") == {"renamed": 1}


def test_user_isolation(client, auth):
    bob_auth = register_user(client, "bob")
    bob_note = _note(client, bob_auth, "B", ["secret"])

    assert _tag_map(client, auth, "note") == {}
    resp = client.post(
        "/api/tags/rename",
        json={"scope": "note", "old_name": "secret", "new_name": "leaked"},
        headers=auth,
    )
    assert resp.json()["data"]["updated"] == 0

    bob_detail = client.get(f"/api/notes/{bob_note['id']}", headers=bob_auth).json()["data"]
    assert bob_detail["tags"] == ["secret"]


def test_blank_name_rejected(client, auth):
    _note(client, auth, "A", ["a"])
    resp = client.post(
        "/api/tags/rename",
        json={"scope": "note", "old_name": "a", "new_name": "   "},
        headers=auth,
    )
    assert resp.status_code == 400
    assert resp.json()["msg"] == "标签名不能为空"
