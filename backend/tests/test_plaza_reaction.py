"""资源广场笔记互动（点赞/收藏）接口测试"""
from tests.conftest import register_user


def _create_note(client, headers, title="测试笔记", content="正文内容"):
    r = client.post(
        "/api/notes",
        json={"title": title, "content": content, "tags": ["python"]},
        headers=headers,
    )
    assert r.status_code == 201
    return r.json()["data"]["id"]


def _publish(client, headers, note_id):
    r = client.put("/api/plaza/publish", json={"type": "note", "id": note_id}, headers=headers)
    assert r.json()["code"] == 200


def test_toggle_like_and_favorite_contract(client, auth):
    """toggle 契约：点赞开→关计数正确；like 与 favorite 互不影响"""
    alice_h = auth
    bob_h = register_user(client, "bob")
    note_id = _create_note(client, alice_h)
    _publish(client, alice_h, note_id)

    # bob 点赞
    r = client.put(f"/api/plaza/note/{note_id}/like", headers=bob_h)
    assert r.json()["code"] == 200
    assert r.json()["data"] == {"liked": True, "like_count": 1}

    # bob 收藏（独立）
    r = client.put(f"/api/plaza/note/{note_id}/favorite", headers=bob_h)
    assert r.json()["data"] == {"favorited": True, "favorite_count": 1}

    # 再点赞 → 取消
    r = client.put(f"/api/plaza/note/{note_id}/like", headers=bob_h)
    assert r.json()["data"] == {"liked": False, "like_count": 0}

    # 收藏状态不受点赞影响
    r = client.get(f"/api/plaza/items/note/{note_id}", headers=bob_h)
    d = r.json()["data"]
    assert d["liked"] is False and d["favorited"] is True
    assert d["like_count"] == 0 and d["favorite_count"] == 1


def test_cannot_react_own_note(client, auth):
    """自己点赞/收藏自己的笔记 → 400 + 6001"""
    alice_h = auth
    note_id = _create_note(client, alice_h)
    _publish(client, alice_h, note_id)

    r = client.put(f"/api/plaza/note/{note_id}/like", headers=alice_h)
    assert r.status_code == 400
    assert r.json()["code"] == 6001

    r = client.put(f"/api/plaza/note/{note_id}/favorite", headers=alice_h)
    assert r.status_code == 400
    assert r.json()["code"] == 6001


def test_react_private_or_missing(client, auth):
    """对私有/不存在笔记 toggle → 404 + 5001"""
    alice_h = auth
    bob_h = register_user(client, "bob")
    private_note = _create_note(client, alice_h)

    r = client.put(f"/api/plaza/note/{private_note}/like", headers=bob_h)
    assert r.status_code == 404
    assert r.json()["code"] == 5001

    r = client.put("/api/plaza/note/999999/favorite", headers=bob_h)
    assert r.status_code == 404
    assert r.json()["code"] == 5001


def test_list_and_detail_enrich(client, auth):
    """列表/详情富化：多人点赞计数、各视角 liked/favorited 正确；prompt 默认值"""
    alice_h = auth
    bob_h = register_user(client, "bob")
    carol_h = register_user(client, "carol")
    note_id = _create_note(client, alice_h)
    _publish(client, alice_h, note_id)

    client.put(f"/api/plaza/note/{note_id}/like", headers=bob_h)
    client.put(f"/api/plaza/note/{note_id}/like", headers=carol_h)
    client.put(f"/api/plaza/note/{note_id}/favorite", headers=bob_h)

    # bob 视角列表
    r = client.get("/api/plaza/items", params={"type": "note"}, headers=bob_h)
    item = r.json()["data"]["items"][0]
    assert item["like_count"] == 2
    assert item["favorite_count"] == 1
    assert item["liked"] is True
    assert item["favorited"] is True

    # alice（作者）视角：计数可见但自己未操作
    r = client.get("/api/plaza/items", params={"type": "note"}, headers=alice_h)
    item = r.json()["data"]["items"][0]
    assert item["like_count"] == 2
    assert item["liked"] is False

    # carol 视角详情
    r = client.get(f"/api/plaza/items/note/{note_id}", headers=carol_h)
    d = r.json()["data"]
    assert d["like_count"] == 2 and d["liked"] is True
    assert d["favorite_count"] == 1 and d["favorited"] is False

    # prompt 列表项互动字段为默认值
    r = client.post(
        "/api/prompts",
        json={"title": "提示词", "content": "x", "tags": ["写作"]},
        headers=alice_h,
    )
    pid = r.json()["data"]["id"]
    client.put("/api/plaza/publish", json={"type": "prompt", "id": pid}, headers=alice_h)
    r = client.get("/api/plaza/items", params={"type": "prompt"}, headers=bob_h)
    p_item = r.json()["data"]["items"][0]
    assert p_item["like_count"] == 0 and p_item["liked"] is False
    assert p_item["favorite_count"] == 0 and p_item["favorited"] is False


def test_my_favorites_and_likes_lists(client, auth):
    """我的点赞/收藏列表：仅自己的、仍 public 的；取消发布后消失；分页 total"""
    alice_h = auth
    bob_h = register_user(client, "bob")
    n1 = _create_note(client, alice_h, title="笔记一")
    n2 = _create_note(client, alice_h, title="笔记二")
    _publish(client, alice_h, n1)
    _publish(client, alice_h, n2)

    client.put(f"/api/plaza/note/{n1}/like", headers=bob_h)
    client.put(f"/api/plaza/note/{n1}/favorite", headers=bob_h)
    client.put(f"/api/plaza/note/{n2}/favorite", headers=bob_h)

    r = client.get("/api/plaza/likes", headers=bob_h)
    data = r.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["id"] == n1

    r = client.get("/api/plaza/favorites", headers=bob_h)
    data = r.json()["data"]
    assert data["total"] == 2
    ids = {i["id"] for i in data["items"]}
    assert ids == {n1, n2}

    # alice 视角列表为空（互动归 bob）
    r = client.get("/api/plaza/favorites", headers=alice_h)
    assert r.json()["data"]["total"] == 0

    # alice 取消发布 n2 → 从 bob 收藏列表消失，但互动行保留（重新发布后恢复）
    client.put("/api/plaza/unpublish", json={"type": "note", "id": n2}, headers=alice_h)
    r = client.get("/api/plaza/favorites", headers=bob_h)
    data = r.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["id"] == n1

    client.put("/api/plaza/publish", json={"type": "note", "id": n2}, headers=alice_h)
    r = client.get("/api/plaza/favorites", headers=bob_h)
    assert r.json()["data"]["total"] == 2

    # 列表项带作者信息与互动计数
    item = r.json()["data"]["items"][0]
    assert item["author_username"] == "alice"
    assert item["favorited"] is True


def test_mine_includes_reaction_counts(client, auth):
    """我的发布管理列表也带互动计数"""
    alice_h = auth
    bob_h = register_user(client, "bob")
    note_id = _create_note(client, alice_h)
    _publish(client, alice_h, note_id)
    client.put(f"/api/plaza/note/{note_id}/like", headers=bob_h)

    r = client.get("/api/plaza/mine", params={"type": "note"}, headers=alice_h)
    item = r.json()["data"]["items"][0]
    assert item["like_count"] == 1
    assert item["liked"] is False
