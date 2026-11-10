"""提示词自动优化器测试 — 一轮流水线、迭代、变量漂移作废、取消与采纳落版本"""

import asyncio
import json

import pytest
from conftest import register_user
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.services.ai.optimizer_service import OPTIMIZER_SERVICE
from app.services.ai.provider import ChatResult

BASELINE_CONTENT = "请把 {{topic}} 讲清楚"
IMPROVED_CONTENT = "请把 {{topic}} 讲清楚，并补充一个可运行的示例"
DRIFT_CONTENT = "请把 {{subject}} 讲清楚，并补充一个可运行的示例"


class FakeOptimizerProvider:
    """假模型：按 system 提示词区分生成 / 评委 / 优化三种调用

    评委打分按用户消息里是否包含改写后的内容来区分基线评测与候选评测。
    """

    def __init__(self, baseline_score: int = 60, candidate_score: int = 90, drift: bool = False):
        self.baseline_score = baseline_score
        self.candidate_score = candidate_score
        self.improved_content = DRIFT_CONTENT if drift else IMPROVED_CONTENT

    async def chat(self, messages, model, temperature: float = 0.2, max_tokens=None) -> ChatResult:
        system = messages[0].get("content", "") if messages else ""
        user = messages[-1].get("content", "") if messages else ""

        if "提示词工程师" in system:
            payload = {
                "analysis": "缺少输出约束",
                "improved_content": self.improved_content,
                "changelog": "补充了示例要求",
            }
            return ChatResult(
                content=json.dumps(payload, ensure_ascii=False),
                tool_calls=[],
                usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                latency_ms=3,
            )

        if "评测员" in system:
            # 评测时 {{topic}} 已被渲染替换，按候选独有的后缀短语区分基线与候选
            is_candidate = "补充一个可运行的示例" in user
            score = self.candidate_score if is_candidate else self.baseline_score
            return ChatResult(
                content=json.dumps({"score": score, "reason": "覆盖了评分要点"}, ensure_ascii=False),
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
def optimizer_ready(client, monkeypatch):
    """开启 AI 开关、替换假模型，并把后台任务替换为 no-op（轮次由测试同步驱动）"""
    monkeypatch.setattr(settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "AI_FAST_MODEL", "test-fast")
    provider = FakeOptimizerProvider()
    monkeypatch.setattr(
        "app.services.ai.optimizer_service.get_chat_provider", lambda: provider
    )
    monkeypatch.setattr("app.services.ai.eval_service.get_chat_provider", lambda: provider)
    monkeypatch.setattr(OPTIMIZER_SERVICE, "_spawn_round_task", lambda run_id, user_id: None)
    return provider


def _user_id(client: TestClient, auth: dict) -> int:
    """从 /auth/me 拿当前用户 id"""
    resp = client.get("/api/auth/me", headers=auth)
    return resp.json()["data"]["id"]


def _create_prompt(client, auth) -> int:
    response = client.post(
        "/api/prompts",
        json={"title": "讲解提示词", "content": BASELINE_CONTENT, "variables": ["topic"]},
        headers=auth,
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


def _create_suite(client, auth, prompt_id: int) -> int:
    response = client.post(
        "/api/ai/eval/suites",
        json={
            "prompt_id": prompt_id,
            "name": "优化评测",
            "cases": [
                {"variables": {"topic": "浏览器缓存"}, "rubric": "必须提到缓存策略"},
            ],
        },
        headers=auth,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["id"]


def _start_run(client, auth, prompt_id: int, suite_id: int, **overrides) -> dict:
    payload = {
        "prompt_id": prompt_id,
        "suite_id": suite_id,
        "max_rounds": 2,
        "score_threshold": 80,
        "temperature": 0.3,
        **overrides,
    }
    response = client.post("/api/ai/prompt-optimizer/runs", json=payload, headers=auth)
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _execute_round(tmp_path, run_id: int, user_id: int) -> None:
    """在测试自身的事件循环里同步执行一轮流水线（后台任务已被 no-op 掉）"""
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}",
        poolclass=NullPool,
    )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def main():
        async with factory() as db:
            await OPTIMIZER_SERVICE._run_round(db, run_id, user_id)

    asyncio.run(main())
    asyncio.run(engine.dispose())


def test_full_round_then_accept(client, auth, optimizer_ready, tmp_path):
    """一轮完整流水线后采纳：落快照版本 + 候选版本，正文同步更新"""
    prompt_id = _create_prompt(client, auth)
    suite_id = _create_suite(client, auth, prompt_id)
    run = _start_run(client, auth, prompt_id, suite_id)
    assert run["status"] == "running"
    assert run["round_number"] == 0

    user_id = _user_id(client, auth)
    _execute_round(tmp_path, run["id"], user_id)

    status = client.get(f"/api/ai/prompt-optimizer/runs/{run['id']}", headers=auth)
    data = status.json()["data"]
    assert data["status"] == "awaiting_review"
    assert data["round_number"] == 1
    assert data["baseline_score"] == 60.0
    assert data["candidate_score"] == 90.0
    assert data["candidate_content"] == IMPROVED_CONTENT
    assert data["analysis"] == "缺少输出约束"
    assert data["changelog"] == "补充了示例要求"

    # 轮次历史可回放
    rounds = client.get(f"/api/ai/prompt-optimizer/runs/{run['id']}/rounds", headers=auth)
    items = rounds.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["status"] == "completed"
    assert items[0]["snapshot"][0]["delta"] == 30.0

    # 采纳：写入两个版本（快照 + 候选），正文更新为候选内容
    accept = client.post(f"/api/ai/prompt-optimizer/runs/{run['id']}/accept", headers=auth)
    assert accept.status_code == 200, accept.text
    accepted = accept.json()["data"]
    assert accepted["status"] == "completed"
    assert accepted["new_version"]["message"] == "补充了示例要求"

    detail = client.get(f"/api/prompts/{prompt_id}", headers=auth).json()["data"]
    assert detail["content"] == IMPROVED_CONTENT

    versions = client.get(f"/api/prompts/{prompt_id}/versions", headers=auth).json()["data"]
    assert versions[0]["message"] == "补充了示例要求"
    assert versions[0]["content"] == IMPROVED_CONTENT
    assert versions[1]["message"] == "自动优化前的快照"
    assert versions[1]["content"] == BASELINE_CONTENT


def _user_id(client: TestClient, auth: dict) -> int:
    """从 /auth/me 拿当前用户 id"""
    resp = client.get("/api/auth/me", headers=auth)
    return resp.json()["data"]["id"]


def test_iterate_runs_second_round(client, auth, optimizer_ready, tmp_path):
    """达标分数线设为 95：首轮 90 分不达标，可继续第二轮"""
    prompt_id = _create_prompt(client, auth)
    suite_id = _create_suite(client, auth, prompt_id)
    run = _start_run(client, auth, prompt_id, suite_id, score_threshold=95)
    user_id = _user_id(client, auth)

    _execute_round(tmp_path, run["id"], user_id)
    iterate = client.post(f"/api/ai/prompt-optimizer/runs/{run['id']}/iterate", headers=auth)
    assert iterate.status_code == 200, iterate.text
    assert iterate.json()["data"]["status"] == "running"

    _execute_round(tmp_path, run["id"], user_id)

    data = client.get(f"/api/ai/prompt-optimizer/runs/{run['id']}", headers=auth).json()["data"]
    assert data["status"] == "awaiting_review"
    assert data["round_number"] == 2

    rounds = client.get(f"/api/ai/prompt-optimizer/runs/{run['id']}/rounds", headers=auth)
    items = rounds.json()["data"]["items"]
    assert [item["round_number"] for item in items] == [1, 2]


def test_variable_drift_skips_round(client, auth, tmp_path):
    """候选丢了 {{变量}} 占位符：本轮作废为 skipped，不产生候选内容"""
    provider = FakeOptimizerProvider(drift=True)
    import app.services.ai.eval_service as eval_module
    import app.services.ai.optimizer_service as optimizer_module

    mp = pytest.MonkeyPatch()
    mp.setattr(settings, "AI_API_KEY", "test-key")
    mp.setattr(optimizer_module, "get_chat_provider", lambda: provider)
    mp.setattr(eval_module, "get_chat_provider", lambda: provider)
    mp.setattr(OPTIMIZER_SERVICE, "_spawn_round_task", lambda run_id, user_id: None)

    prompt_id = _create_prompt(client, auth)
    suite_id = _create_suite(client, auth, prompt_id)
    run = _start_run(client, auth, prompt_id, suite_id)
    user_id = _user_id(client, auth)

    _execute_round(tmp_path, run["id"], user_id)

    data = client.get(f"/api/ai/prompt-optimizer/runs/{run['id']}", headers=auth).json()["data"]
    assert data["status"] == "awaiting_review"
    assert data["candidate_content"] is None
    assert data["candidate_score"] is None
    assert "变量占位符与原文不一致" in data["analysis"]

    rounds = client.get(f"/api/ai/prompt-optimizer/runs/{run['id']}/rounds", headers=auth)
    assert rounds.json()["data"]["items"][0]["status"] == "skipped"

    mp.undo()


def test_cancel_stops_pipeline(client, auth, optimizer_ready, tmp_path):
    """取消会话后：流水线不再推进，也不能继续迭代"""
    prompt_id = _create_prompt(client, auth)
    suite_id = _create_suite(client, auth, prompt_id)
    run = _start_run(client, auth, prompt_id, suite_id)
    user_id = _user_id(client, auth)

    cancel = client.post(f"/api/ai/prompt-optimizer/runs/{run['id']}/cancel", headers=auth)
    assert cancel.status_code == 200
    assert cancel.json()["data"]["status"] == "cancelled"

    _execute_round(tmp_path, run["id"], user_id)

    data = client.get(f"/api/ai/prompt-optimizer/runs/{run['id']}", headers=auth).json()["data"]
    assert data["status"] == "cancelled"
    assert data["round_number"] == 0
    assert data["baseline_score"] is None

    iterate = client.post(f"/api/ai/prompt-optimizer/runs/{run['id']}/iterate", headers=auth)
    assert iterate.status_code == 400


def test_all_cases_pass_threshold_skips_optimization(client, auth, tmp_path):
    """基线已达标：不再调用优化模型，本轮记 skipped"""
    provider = FakeOptimizerProvider(baseline_score=95, candidate_score=95)
    import app.services.ai.eval_service as eval_module
    import app.services.ai.optimizer_service as optimizer_module

    mp = pytest.MonkeyPatch()
    mp.setattr(settings, "AI_API_KEY", "test-key")
    mp.setattr(optimizer_module, "get_chat_provider", lambda: provider)
    mp.setattr(eval_module, "get_chat_provider", lambda: provider)
    mp.setattr(OPTIMIZER_SERVICE, "_spawn_round_task", lambda run_id, user_id: None)

    prompt_id = _create_prompt(client, auth)
    suite_id = _create_suite(client, auth, prompt_id)
    run = _start_run(client, auth, prompt_id, suite_id)
    user_id = _user_id(client, auth)

    _execute_round(tmp_path, run["id"], user_id)

    data = client.get(f"/api/ai/prompt-optimizer/runs/{run['id']}", headers=auth).json()["data"]
    assert data["status"] == "awaiting_review"
    assert data["baseline_score"] == 95.0
    assert data["candidate_content"] is None
    assert "已达到目标分数" in data["analysis"]

    mp.undo()


def test_run_requires_ai_configured(client, auth, monkeypatch):
    """未配置密钥时发起优化直接失败"""
    monkeypatch.setattr(settings, "AI_API_KEY", "")
    prompt_id = _create_prompt(client, auth)
    suite_id = _create_suite(client, auth, prompt_id)

    response = client.post(
        "/api/ai/prompt-optimizer/runs",
        json={"prompt_id": prompt_id, "suite_id": suite_id},
        headers=auth,
    )
    assert response.status_code == 400
    assert response.json()["code"] == 7001


def test_run_belongs_to_owner(client, auth, optimizer_ready):
    """他人不能读取自己的优化会话"""
    other = register_user(client, "opt_owner")
    prompt_id = _create_prompt(client, auth)
    suite_id = _create_suite(client, auth, prompt_id)
    run = _start_run(client, auth, prompt_id, suite_id)

    response = client.get(f"/api/ai/prompt-optimizer/runs/{run['id']}", headers=other)
    assert response.status_code == 404
