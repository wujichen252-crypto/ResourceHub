"""提示词评测实验室测试 — 评测集 CRUD、生成+评委打分、历史留档与降级路径"""

import pytest

from app.core.config import settings
from app.services.ai.provider import AIProviderError, ChatResult
from conftest import register_user


class FakeProvider:
    """假模型：区分生成调用与评委调用，避免测试触网"""

    def __init__(self, score: int = 88, judge_fails: bool = False):
        self.score = score
        self.judge_fails = judge_fails

    async def chat(self, messages, model, temperature: float = 0.2, max_tokens=None) -> ChatResult:
        if messages and messages[0].get("role") == "system":
            if self.judge_fails:
                raise AIProviderError("评委服务不可用")
            return ChatResult(
                content=f'{{"score": {self.score}, "reason": "覆盖了评分要点"}}',
                tool_calls=[],
                usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                latency_ms=3,
            )
        return ChatResult(
            content="生成的输出内容",
            tool_calls=[],
            usage={"prompt_tokens": 8, "completion_tokens": 12, "total_tokens": 20},
            latency_ms=5,
        )


@pytest.fixture()
def ai_enabled(monkeypatch):
    """开启 AI 可用开关并替换为假模型"""
    monkeypatch.setattr(settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "AI_CHAT_MODEL", "test-chat")
    provider = FakeProvider()
    monkeypatch.setattr(
        "app.services.ai.eval_service.get_chat_provider", lambda: provider
    )
    return provider


def _create_prompt(client, auth, content: str = "请把 {{topic}} 讲清楚") -> int:
    """建一个带变量的提示词"""
    response = client.post(
        "/api/prompts",
        json={"title": "讲解提示词", "content": content, "variables": ["topic"]},
        headers=auth,
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


def _create_suite(client, auth, prompt_id: int, cases=None) -> int:
    """建评测集，默认两个用例"""
    payload = {
        "prompt_id": prompt_id,
        "name": "基础评测",
        "cases": cases
        or [
            {"variables": {"topic": "浏览器缓存"}, "rubric": "必须提到缓存策略"},
            {"variables": {"topic": "首屏渲染"}, "rubric": "必须提到渲染流程"},
        ],
    }
    response = client.post("/api/ai/eval/suites", json=payload, headers=auth)
    assert response.status_code == 201, response.text
    return response.json()["data"]["id"]


def test_create_suite_returns_cases(client, auth):
    """创建评测集返回用例与变量（JSON 文本反序列化为对象）"""
    prompt_id = _create_prompt(client, auth)
    response = client.post(
        "/api/ai/eval/suites",
        json={
            "prompt_id": prompt_id,
            "name": "答辩评测",
            "judge_model": "judge-model",
            "cases": [
                {"variables": {"topic": "缓存"}, "expected_output": "答案", "rubric": "要点"}
            ],
        },
        headers=auth,
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["prompt_id"] == prompt_id
    assert data["judge_model"] == "judge-model"
    assert data["case_count"] == 1
    assert data["cases"][0]["variables"] == {"topic": "缓存"}
    assert data["cases"][0]["rubric"] == "要点"


def test_create_suite_rejects_foreign_prompt(client, auth):
    """他人提示词不能建评测集"""
    other = register_user(client, "eval_owner")
    foreign_prompt = _create_prompt(client, other)

    response = client.post(
        "/api/ai/eval/suites",
        json={
            "prompt_id": foreign_prompt,
            "name": "越权评测",
            "cases": [{"variables": {"topic": "x"}}],
        },
        headers=auth,
    )
    assert response.status_code == 400
    assert response.json()["code"] == 4001


def test_run_scores_each_case(client, auth, ai_enabled):
    """执行评测：逐用例生成、打分并返回均分"""
    prompt_id = _create_prompt(client, auth)
    suite_id = _create_suite(client, auth, prompt_id)

    response = client.post(f"/api/ai/eval/suites/{suite_id}/run", json={}, headers=auth)
    assert response.status_code == 200, response.text
    data = response.json()["data"]

    assert data["case_count"] == 2
    assert data["avg_score"] == 88.0
    assert data["model"] == "test-chat"
    assert data["total_tokens"] == 2 * (20 + 15)
    assert all(item["output"] == "生成的输出内容" for item in data["results"])
    # 用例变量带入渲染，确保每条用例用的是自己的取值
    assert {item["variables"]["topic"] for item in data["results"]} == {"浏览器缓存", "首屏渲染"}


def test_run_without_rubric_skips_judge(client, auth, ai_enabled):
    """未设置评分要点时不调用评委，分数留空但仍记录输出"""
    prompt_id = _create_prompt(client, auth)
    suite_id = _create_suite(
        client, auth, prompt_id, cases=[{"variables": {"topic": "无要点"}}]
    )

    response = client.post(f"/api/ai/eval/suites/{suite_id}/run", json={}, headers=auth)
    data = response.json()["data"]
    assert data["avg_score"] is None
    assert data["results"][0]["score"] is None
    assert "未设置评分要点" in data["results"][0]["judge_reason"]


def test_run_survives_judge_failure(client, auth, monkeypatch):
    """评委调用失败时只丢分数，生成结果仍落库"""
    monkeypatch.setattr(settings, "AI_API_KEY", "test-key")
    provider = FakeProvider(judge_fails=True)
    monkeypatch.setattr(
        "app.services.ai.eval_service.get_chat_provider", lambda: provider
    )
    prompt_id = _create_prompt(client, auth)
    suite_id = _create_suite(client, auth, prompt_id)

    response = client.post(f"/api/ai/eval/suites/{suite_id}/run", json={}, headers=auth)
    result = response.json()["data"]["results"][0]
    assert response.status_code == 200
    assert result["score"] is None
    assert "评审 AI 调用失败" in result["judge_reason"]
    assert result["output"] == "生成的输出内容"


def test_run_requires_ai_configured(client, auth, monkeypatch):
    """未配置密钥时评测直接失败，不产生结果"""
    monkeypatch.setattr(settings, "AI_API_KEY", "")
    prompt_id = _create_prompt(client, auth)
    suite_id = _create_suite(client, auth, prompt_id)

    response = client.post(f"/api/ai/eval/suites/{suite_id}/run", json={}, headers=auth)
    assert response.status_code == 400
    assert response.json()["code"] == 7001


def test_results_history_and_version_label(client, auth, ai_enabled):
    """结果按时间倒序留档，指定历史版本时带出版本号"""
    prompt_id = _create_prompt(client, auth, content="旧版本：{{topic}}")
    suite_id = _create_suite(client, auth, prompt_id, cases=[{"variables": {"topic": "缓存"}}])

    # 更新内容会自动快照旧版本
    client.put(f"/api/prompts/{prompt_id}", json={"content": "新版本：{{topic}}"}, headers=auth)
    versions = client.get(f"/api/prompts/{prompt_id}/versions", headers=auth).json()["data"]
    version_id = versions[0]["id"]

    client.post(f"/api/ai/eval/suites/{suite_id}/run", json={}, headers=auth)
    client.post(
        f"/api/ai/eval/suites/{suite_id}/run",
        json={"prompt_version_id": version_id},
        headers=auth,
    )

    response = client.get(f"/api/ai/eval/suites/{suite_id}/results", headers=auth)
    items = response.json()["data"]["items"]
    assert len(items) == 2
    assert items[0]["version_number"] == versions[0]["version_number"]
    assert items[1]["version_number"] is None


def test_list_and_delete_suite(client, auth):
    """按提示词过滤评测集，删除后不再返回"""
    prompt_id = _create_prompt(client, auth)
    suite_id = _create_suite(client, auth, prompt_id)

    listed = client.get(
        "/api/ai/eval/suites", params={"prompt_id": prompt_id}, headers=auth
    ).json()["data"]["items"]
    assert [item["id"] for item in listed] == [suite_id]

    assert client.delete(f"/api/ai/eval/suites/{suite_id}", headers=auth).status_code == 200
    assert client.get(
        "/api/ai/eval/suites", params={"prompt_id": prompt_id}, headers=auth
    ).json()["data"]["items"] == []
