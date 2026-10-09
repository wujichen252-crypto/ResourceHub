"""分类模块回归测试 — 锁定树形结构、类型隔离与级联删除契约"""


def _create_category(client, auth, name, type="note", parent_id=None):
    resp = client.post(
        "/api/categories",
        json={"name": name, "type": type, "parent_id": parent_id},
        headers=auth,
    )
    assert resp.status_code == 201
    return resp.json()["data"]


def test_create_category_contract(client, auth):
    data = _create_category(client, auth, "技术")
    assert {"id", "name", "type", "parent_id", "sort_order", "created_at"} <= set(data)
    assert data["type"] == "note"


def test_tree_nesting_and_type_isolation(client, auth):
    root = _create_category(client, auth, "技术")
    child = _create_category(client, auth, "前端", parent_id=root["id"])
    _create_category(client, auth, "编程", type="prompt")

    note_tree = client.get("/api/categories", params={"type": "note"}, headers=auth).json()["data"]
    assert len(note_tree) == 1
    assert note_tree[0]["id"] == root["id"]
    assert [c["id"] for c in note_tree[0]["children"]] == [child["id"]]
    # 子节点不应同时出现在顶层
    assert all(n["id"] != child["id"] for n in note_tree)

    prompt_tree = client.get("/api/categories", params={"type": "prompt"}, headers=auth).json()["data"]
    assert [n["name"] for n in prompt_tree] == ["编程"]


def test_update_category(client, auth):
    cat = _create_category(client, auth, "旧名")
    resp = client.put(f"/api/categories/{cat['id']}", json={"name": "新名"}, headers=auth)
    assert resp.json()["data"]["name"] == "新名"


def test_update_missing_category_404(client, auth):
    resp = client.put("/api/categories/9999", json={"name": "x"}, headers=auth)
    assert resp.status_code == 404
    assert resp.json()["msg"] == "分类不存在"


def test_delete_category_cascades_children_and_notes(client, auth):
    root = _create_category(client, auth, "待删目录")
    child = _create_category(client, auth, "子目录", parent_id=root["id"])
    note = client.post(
        "/api/notes",
        json={"title": "目录下的笔记", "content": "x", "category_id": child["id"], "tags": []},
        headers=auth,
    ).json()["data"]

    resp = client.delete(f"/api/categories/{root['id']}", headers=auth)
    assert resp.status_code == 200
    assert client.get("/api/categories", params={"type": "note"}, headers=auth).json()["data"] == []
    assert client.get(f"/api/notes/{note['id']}", headers=auth).status_code == 404
