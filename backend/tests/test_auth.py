"""认证模块回归测试 — 锁定现行响应契约（信封结构、状态码、消息文本）"""


def test_register_success(client):
    resp = client.post(
        "/api/auth/register",
        json={"username": "bob", "password": "password123", "email": "bob@example.com"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert set(body) == {"code", "data", "msg"}
    assert set(body["data"]) == {"id", "username", "email", "avatar", "created_at"}
    assert body["data"]["username"] == "bob"


def test_register_duplicate_username_409(client, auth):
    resp = client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "password123", "email": "other@example.com"},
    )
    assert resp.status_code == 409
    assert "已被注册" in resp.json()["msg"]


def test_register_short_password_validation_422(client):
    resp = client.post(
        "/api/auth/register", json={"username": "carol", "password": "123"}
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["msg"] == "请求参数验证失败"
    assert len(body["data"]["errors"]) > 0


def test_login_and_me(client, auth):
    me = client.get("/api/auth/me", headers=auth)
    assert me.status_code == 200
    assert me.json()["data"]["username"] == "alice"


def test_login_wrong_password_401(client):
    client.post(
        "/api/auth/register",
        json={"username": "dave", "password": "password123"},
    )
    resp = client.post(
        "/api/auth/login", json={"username": "dave", "password": "wrongpass1"}
    )
    assert resp.status_code == 401
    assert resp.json()["msg"] == "用户名或密码错误"


def test_me_without_token_401(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
    assert resp.json()["msg"] == "未提供认证令牌"


def test_refresh_flow(client):
    client.post(
        "/api/auth/register",
        json={"username": "erin", "password": "password123"},
    )
    login = client.post(
        "/api/auth/login",
        json={"username": "erin", "password": "password123"},
    )
    refresh_token = login.json()["data"]["refresh_token"]
    resp = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    new_access = resp.json()["data"]["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_access}"})
    assert me.status_code == 200


def test_forgot_password_mismatch_400(client):
    client.post(
        "/api/auth/register",
        json={"username": "frank", "password": "password123", "email": "frank@example.com"},
    )
    resp = client.post(
        "/api/auth/forgot-password",
        json={"username": "frank", "email": "wrong@example.com", "new_password": "newpassword1"},
    )
    assert resp.status_code == 400
    assert resp.json()["msg"] == "用户名或邮箱不匹配"


def test_change_password_wrong_old_400(client, auth):
    resp = client.put(
        "/api/auth/change-password",
        headers=auth,
        json={"old_password": "notmyoldpass", "new_password": "newpassword1"},
    )
    assert resp.status_code == 400
    assert resp.json()["msg"] == "原密码错误"
