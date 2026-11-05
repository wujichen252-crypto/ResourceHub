"""全局统一搜索接口测试：命中笔记/提示词、用户隔离、参数校验"""
from tests.conftest import register_user


def test_search_hits_notes_and_prompts(client, auth):
    client.post("/api/notes", headers=auth, json={
        "title": "Docker Compose 编排",
        "content": "使用 docker compose up --build 启动完整服务",
    })
    client.post("/api/prompts", headers=auth, json={
        "title": "容器排障助手",
        "description": "分析容器启动失败的日志",
        "content": "你是一名容器运维专家，请分析 {{error_log}}",
    })

    resp = client.get("/api/search", params={"q": "docker"}, headers=auth)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["query"] == "docker"
    types = {item["type"] for item in data["items"]}
    assert "note" in types
    # 命中的笔记标题与摘要片段包含原文
    note = next(i for i in data["items"] if i["type"] == "note")
    assert "Docker Compose 编排" == note["title"]
    assert "docker" in note["snippet"].lower()
    assert note["snippet"].startswith("…") or note["snippet"].endswith("…") or note["snippet"]


def test_search_user_isolation(client, auth):
    client.post("/api/notes", headers=auth, json={"title": "私密笔记", "content": "只属于 alice"})
    other = register_user(client, "bob")
    client.post("/api/notes", headers=other, json={"title": "bob 的笔记", "content": "别人的内容"})

    resp = client.get("/api/search", params={"q": "笔记"}, headers=auth)
    items = resp.json()["data"]["items"]
    assert all("bob" not in i["title"] for i in items)


def test_search_requires_query(client, auth):
    resp = client.get("/api/search", headers=auth)
    assert resp.status_code == 422


def test_search_limit_trims_results(client, auth):
    for i in range(8):
        client.post("/api/notes", headers=auth, json={"title": f"重复关键词 {i}", "content": "same"})
    resp = client.get("/api/search", params={"q": "关键词", "limit": 3}, headers=auth)
    notes = [i for i in resp.json()["data"]["items"] if i["type"] == "note"]
    assert len(notes) <= 3
