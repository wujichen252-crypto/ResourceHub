"""工作台统计接口回归测试 — 锁定 /api/stats/overview 响应结构契约"""


def _seed(client, auth):
    """造数：两级分类（根+子）、带标签笔记/提示词、一次提示词使用记录"""
    root = client.post(
        "/api/categories", json={"name": "技术", "type": "note"}, headers=auth
    ).json()["data"]
    child = client.post(
        "/api/categories",
        json={"name": "后端", "type": "note", "parent_id": root["id"]},
        headers=auth,
    ).json()["data"]

    client.post(
        "/api/notes",
        json={"title": "SQLAlchemy 笔记", "content": "ORM", "category_id": child["id"],
              "tags": ["python", "orm"]},
        headers=auth,
    )
    client.post(
        "/api/notes",
        json={"title": "无分类笔记", "content": "x", "category_id": None, "tags": ["python"]},
        headers=auth,
    )
    prompt = client.post(
        "/api/prompts",
        json={"title": "代码审查", "content": "review {{code}}", "tags": ["ai"]},
        headers=auth,
    ).json()["data"]
    client.post(f"/api/prompts/{prompt['id']}/use", headers=auth)
    return root


def test_stats_overview_contract(client, auth):
    root = _seed(client, auth)
    resp = client.get("/api/stats/overview", headers=auth)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert {"tag_cloud", "creation_trend", "category_distribution", "usage_heatmap"} <= set(data)

    tags = {t["name"]: t["value"] for t in data["tag_cloud"]}
    assert tags["python"] == 2 and tags["orm"] == 1 and tags["ai"] == 1

    trend = data["creation_trend"]
    assert len(trend) == 30
    assert all({"date", "notes", "prompts"} <= set(p) for p in trend)
    assert sum(p["notes"] for p in trend) == 2
    assert sum(p["prompts"] for p in trend) == 1

    dist = {d["name"]: d["value"] for d in data["category_distribution"]}
    assert dist["技术"] == 1  # 子分类回溯到一级分类
    assert dist["未分类"] == 1

    heatmap = data["usage_heatmap"]
    assert len(heatmap) == 1
    assert heatmap[0]["count"] == 1
    assert root["id"] > 0


def test_stats_requires_auth(client):
    resp = client.get("/api/stats/overview")
    assert resp.status_code == 401


def test_stats_user_isolation(client, auth):
    from conftest import register_user

    _seed(client, auth)
    bob = register_user(client, "bob_stats")
    data = client.get("/api/stats/overview", headers=bob).json()["data"]
    assert data["tag_cloud"] == []
    assert sum(p["notes"] for p in data["creation_trend"]) == 0
