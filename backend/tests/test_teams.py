"""团队知识库测试：成员关系、资源隔离与权限矩阵"""

from conftest import register_user

TEAM_PAYLOAD = {"name": "研发知识库", "description": "团队共享的技术笔记"}


def _create_team(client, headers, payload=None) -> dict:
    resp = client.post("/api/teams", json=payload or TEAM_PAYLOAD, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def test_create_and_list_team(client, auth):
    team = _create_team(client, auth)
    assert team["role"] == "owner"
    assert team["member_count"] == 1
    assert len(team["invite_code"]) == 8

    resp = client.get("/api/teams", headers=auth)
    assert resp.status_code == 200
    teams = resp.json()["data"]
    assert [item["id"] for item in teams] == [team["id"]]


def test_join_by_invite_code_and_role_management(client, auth):
    team = _create_team(client, auth)
    bob = register_user(client, "bob")

    # 重复加入应被拒绝
    first = client.post("/api/teams/join", json={"invite_code": team["invite_code"]}, headers=bob)
    assert first.status_code == 200
    again = client.post("/api/teams/join", json={"invite_code": team["invite_code"]}, headers=bob)
    assert again.status_code == 409

    members = client.get(f"/api/teams/{team['id']}/members", headers=auth).json()["data"]
    assert {m["username"] for m in members} == {"alice", "bob"}
    bob_id = next(m["user_id"] for m in members if m["username"] == "bob")

    # 创建者可将成员提升为管理员
    promoted = client.put(
        f"/api/teams/{team['id']}/members/{bob_id}", json={"role": "admin"}, headers=auth
    )
    assert promoted.status_code == 200
    assert promoted.json()["data"]["role"] == "admin"

    # 管理员不能移除创建者
    alice_id = next(m["user_id"] for m in members if m["username"] == "alice")
    denied = client.delete(f"/api/teams/{team['id']}/members/{alice_id}", headers=bob)
    assert denied.status_code == 403

    # 创建者移除成员后，该成员失去访问权
    removed = client.delete(f"/api/teams/{team['id']}/members/{bob_id}", headers=auth)
    assert removed.status_code == 200
    assert client.get(f"/api/teams/{team['id']}", headers=bob).status_code == 403


def test_owner_cannot_leave_team(client, auth):
    team = _create_team(client, auth)
    resp = client.post(f"/api/teams/{team['id']}/leave", headers=auth)
    assert resp.status_code == 400


def test_team_note_visibility_and_edit_permission(client, auth):
    team = _create_team(client, auth)
    bob = register_user(client, "bob")
    client.post("/api/teams/join", json={"invite_code": team["invite_code"]}, headers=bob)
    carol = register_user(client, "carol")

    created = client.post(
        "/api/notes",
        json={"title": "团队规范", "content": "所有接口必须写单元测试", "team_id": team["id"]},
        headers=auth,
    )
    assert created.status_code == 201, created.text
    note_id = created.json()["data"]["id"]

    # 团队成员可读，非成员按不存在处理
    assert client.get(f"/api/notes/{note_id}", headers=bob).status_code == 200
    assert client.get(f"/api/notes/{note_id}", headers=carol).status_code == 404

    # 团队列表可见，个人列表不混入
    team_notes = client.get(f"/api/notes?team_id={team['id']}", headers=bob).json()["data"]
    assert [item["id"] for item in team_notes["items"]] == [note_id]
    personal = client.get("/api/notes", headers=auth).json()["data"]
    assert personal["items"] == []

    # 普通成员不能修改他人创建的团队笔记
    denied = client.put(f"/api/notes/{note_id}", json={"title": "被篡改"}, headers=bob)
    assert denied.status_code == 403

    # 提升为管理员后可协同编辑
    bob_id = next(m["user_id"] for m in client.get(f"/api/teams/{team['id']}/members", headers=auth).json()["data"] if m["username"] == "bob")
    client.put(f"/api/teams/{team['id']}/members/{bob_id}", json={"role": "admin"}, headers=auth)
    updated = client.put(f"/api/notes/{note_id}", json={"title": "团队规范 v2"}, headers=bob)
    assert updated.status_code == 200
    assert updated.json()["data"]["title"] == "团队规范 v2"


def test_non_member_cannot_create_team_resource(client, auth):
    team = _create_team(client, auth)
    carol = register_user(client, "carol")

    resp = client.post(
        "/api/notes",
        json={"title": "越权写入", "content": "x", "team_id": team["id"]},
        headers=carol,
    )
    assert resp.status_code == 403

    prompts = client.get(f"/api/prompts?team_id={team['id']}", headers=carol)
    assert prompts.status_code == 403


def test_team_prompt_shares_across_members(client, auth):
    team = _create_team(client, auth)
    bob = register_user(client, "bob")
    client.post("/api/teams/join", json={"invite_code": team["invite_code"]}, headers=bob)

    created = client.post(
        "/api/prompts",
        json={"title": "代码评审", "content": "请评审 {{language}} 代码", "team_id": team["id"]},
        headers=auth,
    )
    assert created.status_code == 201, created.text
    prompt_id = created.json()["data"]["id"]

    detail = client.get(f"/api/prompts/{prompt_id}", headers=bob)
    assert detail.status_code == 200
    assert detail.json()["data"]["team_id"] == team["id"]

    listing = client.get(f"/api/prompts?team_id={team['id']}", headers=bob).json()["data"]
    assert [item["id"] for item in listing["items"]] == [prompt_id]


def test_delete_team_returns_resources_to_author(client, auth):
    team = _create_team(client, auth)
    note_id = client.post(
        "/api/notes",
        json={"title": "临时团队笔记", "content": "内容", "team_id": team["id"]},
        headers=auth,
    ).json()["data"]["id"]

    assert client.delete(f"/api/teams/{team['id']}", headers=auth).status_code == 200
    # 团队解散后笔记回落个人空间，作者仍可访问
    detail = client.get(f"/api/notes/{note_id}", headers=auth)
    assert detail.status_code == 200
    assert detail.json()["data"]["team_id"] is None
