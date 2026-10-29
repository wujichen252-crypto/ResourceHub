"""智能体人格测试 — CRUD、默认人格唯一、归属隔离与兜底"""

from conftest import register_user

PROFILE_PAYLOAD = {
    "name": "阿枢",
    "persona": "你的前端学习搭档",
    "tone": "严谨",
    "expertise": "Vue 3 / TypeScript",
    "boundaries": "不替我直接改代码，先解释思路",
    "greeting": "今天想推进哪一块？",
}


def test_profile_crud_and_default(client, auth):
    """首个创建的人格自动成为默认，激活切换后旧默认被取消"""
    empty = client.get("/api/ai/profiles", headers=auth)
    assert empty.status_code == 200
    assert empty.json()["data"]["items"] == []

    created = client.post("/api/ai/profiles", json=PROFILE_PAYLOAD, headers=auth)
    assert created.status_code == 201
    first = created.json()["data"]
    assert first["is_default"] is True

    status = client.get("/api/ai/status", headers=auth).json()["data"]
    assert status["active_profile"]["name"] == "阿枢"

    second = client.post(
        "/api/ai/profiles",
        json={**PROFILE_PAYLOAD, "name": "写作搭档", "is_default": False},
        headers=auth,
    ).json()["data"]
    assert second["is_default"] is False

    activated = client.put(
        f"/api/ai/profiles/{second['id']}/activate", headers=auth
    ).json()["data"]
    assert activated["is_default"] is True

    listing = client.get("/api/ai/profiles", headers=auth).json()["data"]["items"]
    by_id = {item["id"]: item for item in listing}
    assert by_id[first["id"]]["is_default"] is False
    assert by_id[second["id"]]["is_default"] is True

    updated = client.put(
        f"/api/ai/profiles/{second['id']}",
        json={"tone": "轻松", "greeting": "慢慢来，先把一个问题讲透。"},
        headers=auth,
    ).json()["data"]
    assert updated["tone"] == "轻松"
    assert updated["greeting"] == "慢慢来，先把一个问题讲透。"

    deleted = client.delete(f"/api/ai/profiles/{second['id']}", headers=auth)
    assert deleted.status_code == 200
    remaining = client.get("/api/ai/profiles", headers=auth).json()["data"]["items"]
    assert len(remaining) == 1
    assert remaining[0]["is_default"] is True


def test_profile_ownership_isolation(client):
    """他人不能读取或修改不属于自己的人格"""
    alice = register_user(client, "alice")
    bob = register_user(client, "bob")
    profile = client.post(
        "/api/ai/profiles", json=PROFILE_PAYLOAD, headers=alice
    ).json()["data"]

    response = client.put(
        f"/api/ai/profiles/{profile['id']}", json={"name": "改名"}, headers=bob
    )
    assert response.status_code == 400
    assert response.json()["code"] == 7007

    delete = client.delete(f"/api/ai/profiles/{profile['id']}", headers=bob)
    assert delete.status_code == 400
    assert delete.json()["code"] == 7007


def test_status_returns_fallback_persona(client, auth):
    """未配置人格时返回内置兜底，避免空态"""
    data = client.get("/api/ai/status", headers=auth).json()["data"]
    assert data["active_profile"]["name"] == "知识助手"
    assert data["active_profile"]["greeting"]


def test_chat_prompt_injects_persona_and_memory():
    """问答系统提示必须包含人格与记忆，且人格在记忆之前"""
    from app.schemas.ai import ChatRequest
    from app.services.ai.chat_service import ChatService

    messages = ChatService._build_messages(
        ChatRequest(message="我在学什么？"),
        [],
        "你是阿枢，语气严谨",
        "<memory_context>\n- [目标] 学会 Vue 3\n</memory_context>",
    )
    system = messages[0]["content"]
    assert "你是阿枢" in system
    assert "<memory_context>" in system
    assert system.index("你是阿枢") < system.index("<memory_context>")
    assert "你的笔记中没有相关内容" in system
