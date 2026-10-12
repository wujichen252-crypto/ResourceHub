"""资源广场（分享/fork）接口测试"""
from tests.conftest import register_user


def _create_note(client, headers, title="测试笔记", content="正文内容", tags=None):
    r = client.post(
        "/api/notes",
        json={"title": title, "content": content, "tags": tags or ["python"]},
        headers=headers,
    )
    assert r.status_code == 201
    return r.json()["data"]["id"]


def _create_prompt(client, headers, title="测试提示词", content="提示词正文"):
    r = client.post(
        "/api/prompts",
        json={"title": title, "content": content, "tags": ["写作"]},
        headers=headers,
    )
    assert r.status_code == 201
    return r.json()["data"]["id"]


def test_publish_and_list_contract(client, auth):
    """契约：发布后广场列表含该条且带 author_username；取消发布后消失"""
    alice_h = auth
    note_id = _create_note(client, alice_h)

    # 未发布：广场不可见
    r = client.get("/api/plaza/items", params={"type": "note"}, headers=alice_h)
    assert r.json()["data"]["total"] == 0

    # 发布
    r = client.put("/api/plaza/publish", json={"type": "note", "id": note_id}, headers=alice_h)
    assert r.json()["code"] == 200
    assert r.json()["data"]["visibility"] == "public"

    r = client.get("/api/plaza/items", params={"type": "note"}, headers=alice_h)
    data = r.json()["data"]
    assert data["total"] == 1
    item = data["items"][0]
    assert item["id"] == note_id
    assert item["type"] == "note"
    assert item["author_username"] == "alice"
    assert "content_preview" in item

    # 详情可读
    r = client.get(f"/api/plaza/items/note/{note_id}", headers=alice_h)
    assert r.json()["data"]["content"] == "正文内容"

    # 取消发布后消失
    r = client.put("/api/plaza/unpublish", json={"type": "note", "id": note_id}, headers=alice_h)
    assert r.json()["data"]["visibility"] == "private"
    r = client.get("/api/plaza/items", params={"type": "note"}, headers=alice_h)
    assert r.json()["data"]["total"] == 0
    r = client.get(f"/api/plaza/items/note/{note_id}", headers=alice_h)
    assert r.status_code == 404
    assert r.json()["code"] == 5001


def test_permission_and_isolation(client, auth):
    """权限与隔离：他人不能发布我的内容；未发布内容他人不可见"""
    alice_h = auth
    bob_h = register_user(client, "bob")
    note_id = _create_note(client, alice_h)

    # bob 不能发布 alice 的笔记（归属校验 → 404，不泄露存在性）
    r = client.put("/api/plaza/publish", json={"type": "note", "id": note_id}, headers=bob_h)
    assert r.status_code == 404

    # alice 发布后，bob 可见但仅只读；alice 私有内容 bob 不可见
    prompt_id = _create_prompt(client, alice_h)
    client.put("/api/plaza/publish", json={"type": "prompt", "id": prompt_id}, headers=alice_h)
    r = client.get("/api/plaza/items", params={"type": "prompt"}, headers=bob_h)
    assert r.json()["data"]["total"] == 1
    assert r.json()["data"]["items"][0]["author_username"] == "alice"

    # bob 自己的广场列表不含 alice 未发布笔记
    r = client.get("/api/plaza/items", params={"type": "note"}, headers=bob_h)
    assert r.json()["data"]["total"] == 0

    # 未认证 → 401
    r = client.get("/api/plaza/items", params={"type": "note"})
    assert r.status_code == 401


def test_fork_copy(client, auth):
    """fork 正确性：副本归 bob、category 空、tags 相等、usage_count=0、署名溯源"""
    alice_h = auth
    bob_h = register_user(client, "bob")
    note_id = _create_note(client, alice_h, title="好笔记", content="内容", tags=["ai", "python"])
    prompt_id = _create_prompt(client, alice_h, title="好提示词")
    client.put("/api/plaza/publish", json={"type": "note", "id": note_id}, headers=alice_h)
    client.put("/api/plaza/publish", json={"type": "prompt", "id": prompt_id}, headers=alice_h)

    # bob fork 笔记
    r = client.post("/api/plaza/fork", json={"type": "note", "id": note_id}, headers=bob_h)
    assert r.json()["code"] == 201
    copy_id = r.json()["data"]["id"]

    # 副本在 bob 的私有列表中，category 为空、tags 相等
    r = client.get("/api/notes", headers=bob_h)
    copies = [n for n in r.json()["data"]["items"] if n["id"] == copy_id]
    assert len(copies) == 1
    assert copies[0]["category_id"] is None
    assert sorted(copies[0]["tags"]) == ["ai", "python"]

    # bob fork 提示词后 usage_count 归零
    r = client.post("/api/plaza/fork", json={"type": "prompt", "id": prompt_id}, headers=bob_h)
    p_copy_id = r.json()["data"]["id"]
    r = client.get(f"/api/prompts/{p_copy_id}", headers=bob_h)
    assert r.json()["data"]["usage_count"] == 0

    # 广场详情中副本来源信息：原内容 forked_from 为 None
    r = client.get(f"/api/plaza/items/note/{note_id}", headers=bob_h)
    assert r.json()["data"]["forked_from"] is None

    # alice 删除原笔记后，bob 的副本仍存在（无级联）
    client.delete(f"/api/notes/{note_id}", headers=alice_h)
    r = client.get(f"/api/notes/{copy_id}", headers=bob_h)
    assert r.status_code == 200


def test_invalid_type_param(client, auth):
    """参数校验：type 非法 → 400/5002；Pydantic Literal 拦截 → 422"""
    r = client.get("/api/plaza/items", params={"type": "blog"}, headers=auth)
    assert r.status_code in (400, 422)
    if r.status_code == 400:
        assert r.json()["detail"]["code"] == 5002

    r = client.put("/api/plaza/publish", json={"type": "blog", "id": 1}, headers=auth)
    assert r.status_code == 422  # Literal 校验


def test_mine_management(client, auth):
    """我的发布管理：/mine 仅返回自己 public 内容"""
    alice_h = auth
    bob_h = register_user(client, "bob")
    note_id = _create_note(client, alice_h)
    bob_note = _create_note(client, bob_h, title="bob私有")
    client.put("/api/plaza/publish", json={"type": "note", "id": note_id}, headers=alice_h)

    r = client.get("/api/plaza/mine", params={"type": "note"}, headers=alice_h)
    data = r.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["id"] == note_id

    # bob 没有发布任何内容
    r = client.get("/api/plaza/mine", params={"type": "note"}, headers=bob_h)
    assert r.json()["data"]["total"] == 0
