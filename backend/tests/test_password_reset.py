"""
密码重置（邮箱验证码）回归测试

邮件发送通过 monkeypatch 注入假实现，不触碰真实 SMTP；
限流参数直接改 settings，避免测试等待真实冷却时间。
"""

import asyncio
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models.password_reset import PasswordResetToken
from app.services.email_service import email_service
from app.services.password_reset_service import RESET_CODE_SENT_MESSAGE

EMAIL = "alice@example.com"
GENERIC_MSG = RESET_CODE_SENT_MESSAGE


def _register(client, username="alice", email=EMAIL):
    resp = client.post(
        "/api/auth/register",
        json={"username": username, "password": "password123", "email": email},
    )
    assert resp.status_code == 201
    return resp.json()["data"]


def _request_code(client, username="alice", email=EMAIL):
    return client.post(
        "/api/auth/password-reset/request",
        json={"username": username, "email": email},
    )


def _confirm(client, code, username="alice", email=EMAIL, new_password="newpassword123"):
    return client.post(
        "/api/auth/password-reset/confirm",
        json={
            "username": username,
            "email": email,
            "code": code,
            "new_password": new_password,
        },
    )


async def _with_session(db_url, fn):
    engine = create_async_engine(db_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with session_factory() as session:
            return await fn(session)
    finally:
        await engine.dispose()


def _tokens(db_url):
    async def run(session):
        result = await session.execute(select(PasswordResetToken).order_by(PasswordResetToken.id))
        return list(result.scalars())

    return asyncio.run(_with_session(db_url, run))


def _patch_token(db_url, token_id, **values):
    async def run(session):
        token = await session.get(PasswordResetToken, token_id)
        for key, value in values.items():
            setattr(token, key, value)
        await session.commit()

    asyncio.run(_with_session(db_url, run))


@pytest.fixture()
def outbox(monkeypatch):
    messages = []

    async def fake_send(to_email, username, code, ttl_minutes):
        messages.append({"to": to_email, "username": username, "code": code})

    monkeypatch.setattr(email_service, "is_configured", lambda: True)
    monkeypatch.setattr(email_service, "send_password_reset_code", fake_send)
    return messages


def test_request_code_sends_mail_and_stores_only_hash(client, outbox, db_url):
    user = _register(client)

    resp = _request_code(client)

    assert resp.status_code == 200
    assert resp.json()["msg"] == GENERIC_MSG
    assert len(outbox) == 1
    assert outbox[0]["to"] == EMAIL
    code = outbox[0]["code"]
    assert len(code) == 6 and code.isdigit()

    tokens = _tokens(db_url)
    assert len(tokens) == 1
    token = tokens[0]
    assert token.user_id == user["id"]
    assert token.code_hash != code
    assert len(token.code_hash) == 64
    assert token.attempts == 0
    assert token.used_at is None
    assert token.expires_at > datetime.now()


def test_request_code_unknown_account_is_indistinguishable(client, outbox, db_url):
    existing = _register(client)
    _request_code(client)
    assert len(outbox) == 1

    unknown = _request_code(client, username="nobody", email="nobody@example.com")

    assert unknown.status_code == 200
    assert unknown.json()["msg"] == GENERIC_MSG
    assert len(outbox) == 1
    assert len(_tokens(db_url)) == 1
    assert existing["username"] == "alice"


def test_request_code_mismatched_email_is_indistinguishable(client, outbox, db_url):
    _register(client)
    resp = _request_code(client, email="wrong@example.com")
    assert resp.status_code == 200
    assert resp.json()["msg"] == GENERIC_MSG
    assert outbox == []
    assert _tokens(db_url) == []


def test_request_code_requires_bound_email(client, outbox, db_url):
    client.post(
        "/api/auth/register",
        json={"username": "noemail", "password": "password123"},
    )
    resp = _request_code(client, username="noemail", email="noemail@example.com")
    assert resp.status_code == 200
    assert outbox == []
    assert _tokens(db_url) == []


def test_resend_cooldown_blocks_second_mail(client, outbox, db_url):
    _register(client)
    first = _request_code(client)
    second = _request_code(client)

    assert first.status_code == second.status_code == 200
    assert len(outbox) == 1
    assert len(_tokens(db_url)) == 1


def test_daily_limit_blocks_after_threshold(client, outbox, db_url, monkeypatch):
    monkeypatch.setattr(settings, "RESET_CODE_RESEND_COOLDOWN_SECONDS", 0)
    monkeypatch.setattr(settings, "RESET_CODE_DAILY_LIMIT", 2)
    _register(client)

    for _ in range(3):
        assert _request_code(client).status_code == 200

    assert len(outbox) == 2
    assert len(_tokens(db_url)) == 2


def test_new_code_invalidates_previous_code(client, outbox, db_url, monkeypatch):
    monkeypatch.setattr(settings, "RESET_CODE_RESEND_COOLDOWN_SECONDS", 0)
    _register(client)
    _request_code(client)
    first_code = outbox[0]["code"]
    _request_code(client)
    second_code = outbox[1]["code"]

    stale = _confirm(client, first_code)
    assert stale.status_code == 400
    assert stale.json()["msg"] == "验证码不正确"

    ok = _confirm(client, second_code)
    assert ok.status_code == 200
    assert ok.json()["msg"] == "密码重置成功，请使用新密码登录"


def test_confirm_resets_password_and_is_one_time(client, outbox):
    _register(client)
    _request_code(client)
    code = outbox[0]["code"]

    ok = _confirm(client, code)
    assert ok.status_code == 200

    new_login = client.post(
        "/api/auth/login", json={"username": "alice", "password": "newpassword123"}
    )
    assert new_login.status_code == 200
    old_login = client.post(
        "/api/auth/login", json={"username": "alice", "password": "password123"}
    )
    assert old_login.status_code == 401

    replay = _confirm(client, code, new_password="anotherpass123")
    assert replay.status_code == 400
    assert replay.json()["msg"] == "验证码无效或已过期"


def test_wrong_code_attempts_then_lockout(client, outbox, db_url, monkeypatch):
    monkeypatch.setattr(settings, "RESET_CODE_MAX_ATTEMPTS", 3)
    _register(client)
    _request_code(client)
    code = outbox[0]["code"]
    wrong = "000000" if code != "000000" else "111111"

    first = _confirm(client, wrong)
    second = _confirm(client, wrong)
    assert first.json()["msg"] == "验证码不正确"
    assert second.json()["msg"] == "验证码不正确"
    assert _tokens(db_url)[0].attempts == 2

    locked = _confirm(client, wrong)
    assert locked.status_code == 400
    assert locked.json()["msg"] == "验证码错误次数过多，请重新获取"
    assert _tokens(db_url)[0].used_at is not None

    correct_after_lock = _confirm(client, code)
    assert correct_after_lock.status_code == 400
    assert correct_after_lock.json()["msg"] == "验证码无效或已过期"


def test_expired_code_rejected(client, outbox, db_url, monkeypatch):
    _register(client)
    _request_code(client)
    expired_code = outbox[0]["code"]
    token = _tokens(db_url)[0]
    _patch_token(db_url, token.id, expires_at=datetime.now() - timedelta(minutes=1))

    resp = _confirm(client, expired_code)
    assert resp.status_code == 400
    assert resp.json()["msg"] == "验证码已过期，请重新获取"
    assert _tokens(db_url)[0].used_at is not None

    monkeypatch.setattr(settings, "RESET_CODE_RESEND_COOLDOWN_SECONDS", 0)
    _request_code(client)
    assert _confirm(client, outbox[1]["code"]).status_code == 200


def test_confirm_without_request_is_rejected(client):
    _register(client)
    resp = _confirm(client, "123456")
    assert resp.status_code == 400
    assert resp.json()["msg"] == "验证码无效或已过期"


def test_code_format_validated(client, outbox):
    _register(client)
    resp = _confirm(client, "12345")
    assert resp.status_code == 422


def test_email_not_configured_returns_503(client, monkeypatch):
    monkeypatch.setattr(email_service, "is_configured", lambda: False)
    _register(client)
    resp = _request_code(client)
    assert resp.status_code == 503
    assert resp.json()["msg"] == "邮件服务未配置，暂时无法发送验证码"


def test_send_failure_invalidates_code_and_returns_502(client, db_url, monkeypatch):
    async def broken_send(to_email, username, code, ttl_minutes):
        raise RuntimeError("smtp down")

    monkeypatch.setattr(email_service, "is_configured", lambda: True)
    monkeypatch.setattr(email_service, "send_password_reset_code", broken_send)
    _register(client)

    resp = _request_code(client)
    assert resp.status_code == 502
    assert resp.json()["msg"] == "验证码发送失败，请稍后再试"
    assert len(_tokens(db_url)) == 1
    assert _tokens(db_url)[0].used_at is not None
