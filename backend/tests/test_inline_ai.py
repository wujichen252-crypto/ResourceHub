"""笔记内联 AI 测试 — 三种动作的 prompt 拼装、参数校验与未配置兜底"""

import pytest
from conftest import register_user

from app.core.config import settings
from app.services.ai.provider import ChatResult


class FakeInlineProvider:
    """假模型：记录调用入参，返回固定结果，避免测试触网"""

    def __init__(self):
        self.calls: list[dict] = []

    async def chat(self, messages, model, temperature: float = 0.2, max_tokens=None) -> ChatResult:
        self.calls.append(
            {
                "messages": messages,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        return ChatResult(
            content="  AI 的输出结果  ",
            tool_calls=[],
            usage={"prompt_tokens": 30, "completion_tokens": 20, "total_tokens": 50},
            latency_ms=8,
        )


@pytest.fixture()
def inline_provider(client, auth, monkeypatch):
    """开启 AI 可用开关并替换内联服务的模型客户端"""
    monkeypatch.setattr(settings, "AI_API_KEY", "test-key")
    provider = FakeInlineProvider()
    monkeypatch.setattr(
        "app.services.ai.inline_service.get_chat_provider", lambda: provider
    )
    return provider


def _post_inline(client, auth, action: str, **overrides) -> dict:
    """调用内联 AI 端点，返回响应 JSON"""
    payload = {"action": action, "text": "选中的原文内容"}
    payload.update(overrides)
    return client.post("/api/ai/note/inline", json=payload, headers=auth).json()


def test_inline_explain_builds_context_prompt(client, auth, inline_provider):
    """解释动作：安全护栏 + 笔记语境进入 system，动作指令进入 user"""
    data = _post_inline(
        client,
        auth,
        "explain",
        note_title="HTTP 缓存笔记",
        context_before="前文内容",
        context_after="后文内容",
    )["data"]

    assert data["action"] == "explain"
    assert data["result"] == "AI 的输出结果"  # 首尾空白被去除
    assert data["model"] == settings.AI_FAST_MODEL
    assert data["tokens"] == 50

    call = inline_provider.calls[0]
    assert call["model"] == settings.AI_FAST_MODEL
    assert call["max_tokens"] == 800
    assert call["temperature"] == 0.3

    system, user = call["messages"]
    assert system["role"] == "system"
    assert "ResourceHub 的个人知识助手" in system["content"]  # SYSTEM_GUARD 前缀
    assert "HTTP 缓存笔记" in system["content"]
    assert "【前文】前文内容" in system["content"]
    assert "【选中文本】选中的原文内容" in system["content"]
    assert "【后文】后文内容" in system["content"]
    assert user["content"].startswith("解释【选中文本】")


def test_inline_rewrite_defaults_and_instruction(client, auth, inline_provider):
    """改写动作：带附加要求时用原文指令，温度 0.5"""
    _post_inline(client, auth, "rewrite", instruction="更口语化一些")

    call = inline_provider.calls[0]
    assert call["temperature"] == 0.5
    assert "更口语化一些" in call["messages"][1]["content"]
    assert call["messages"][1]["content"].startswith("改写【选中文本】")


def test_inline_rewrite_without_instruction_uses_default(client, auth, inline_provider):
    """改写未带附加要求时使用默认润色指令"""
    _post_inline(client, auth, "rewrite")
    assert "润色，使表达更清晰流畅" in inline_provider.calls[0]["messages"][1]["content"]


def test_inline_ask_contains_question(client, auth, inline_provider):
    """提问动作：追加问题进入 user 消息"""
    _post_inline(client, auth, "ask", instruction="这段话是什么意思？")

    user = inline_provider.calls[0]["messages"][1]["content"]
    assert user.startswith("基于【选中文本】及上下文回答用户问题：")
    assert "这段话是什么意思？" in user


def test_inline_rejects_overlong_text(client, auth):
    """选中文本超过 2000 字时参数校验失败"""
    response = client.post(
        "/api/ai/note/inline",
        json={"action": "explain", "text": "字" * 2001},
        headers=auth,
    )
    assert response.status_code == 422


def test_inline_rejects_unknown_action(client, auth):
    """非法动作类型被 Pydantic 拒绝"""
    response = client.post(
        "/api/ai/note/inline",
        json={"action": "translate", "text": "内容"},
        headers=auth,
    )
    assert response.status_code == 422


def test_inline_requires_ai_configured(client, auth, monkeypatch):
    """未配置密钥时直接返回 7001，不调用模型"""
    monkeypatch.setattr(settings, "AI_API_KEY", "")
    response = client.post(
        "/api/ai/note/inline",
        json={"action": "explain", "text": "内容"},
        headers=auth,
    )
    assert response.json()["code"] == 7001
