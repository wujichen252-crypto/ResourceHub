"""提示词评测实验室

流程：按用例渲染提示词 → 调用对话模型生成 → 由评委模型结构化打分 → 结果留档。
所有模型调用都会记入用量表，评测同样受每日额度约束。
"""

import json
import logging
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.errors import ErrorCode
from app.core.response import APIError
from app.models.ai import PromptEvalCase, PromptEvalResult, PromptEvalSuite
from app.models.prompt import Prompt, PromptVersion
from app.schemas.ai import EvalRunRequest, EvalSuiteCreate
from app.services.ai.provider import AIProviderError, OpenAICompatibleProvider, get_chat_provider
from app.services.ai.usage import ensure_quota, record_usage
from app.services.prompt_service import render_template

logger = logging.getLogger(__name__)

JUDGE_SYSTEM = (
    "你是严格的提示词评测员。请依据评分要点，从需求覆盖、准确性、可执行性、表达清晰度四个维度评估实际输出。"
    '只返回一个 JSON 对象，不要输出其他文字，格式为 {"score": 0 到 100 的整数, "reason": "不超过 80 字的中文理由"}。'
)


def _load_json(raw: str | None, fallback: Any) -> Any:
    """解析数据库中以 JSON 文本存储的字段"""
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def _parse_judge(text: str) -> tuple[float | None, str]:
    """解析评委输出：优先取 JSON 对象，退化到抓第一个 0-100 数字"""
    raw = (text or "").strip()
    matched = re.search(r"\{.*\}", raw, re.S)
    if matched:
        try:
            data = json.loads(matched.group(0))
            score = float(data.get("score"))
            reason = str(data.get("reason") or "").strip()
            return min(100.0, max(0.0, score)), reason or "评审 AI 未给出理由"
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    number = re.search(r"\b(\d{1,3})\b", raw)
    if number:
        return min(100.0, max(0.0, float(number.group(1)))), raw[:200]
    return None, (raw[:200] or "无法读取评审 AI 的打分")


def _case_out(case: PromptEvalCase) -> dict[str, Any]:
    """用例输出结构"""
    return {
        "id": case.id,
        "variables": _load_json(case.variables, {}),
        "expected_output": case.expected_output,
        "rubric": case.rubric,
    }


def _suite_out(suite: PromptEvalSuite, with_cases: bool = True) -> dict[str, Any]:
    """评测集输出结构"""
    data: dict[str, Any] = {
        "id": suite.id,
        "prompt_id": suite.prompt_id,
        "name": suite.name,
        "description": suite.description,
        "judge_model": suite.judge_model,
        "case_count": len(suite.cases) if suite.cases is not None else 0,
        "created_at": suite.created_at.isoformat() if suite.created_at else None,
    }
    if with_cases:
        data["cases"] = [_case_out(case) for case in sorted(suite.cases, key=lambda c: c.id or 0)]
    return data


def _result_out(result: PromptEvalResult, version_number: int | None) -> dict[str, Any]:
    """评测结果输出结构"""
    return {
        "id": result.id,
        "suite_id": result.suite_id,
        "case_id": result.case_id,
        "prompt_version_id": result.prompt_version_id,
        "version_number": version_number,
        "model": result.model,
        "output": result.output,
        "score": result.score,
        "judge_reason": result.judge_reason,
        "latency_ms": result.latency_ms,
        "total_tokens": result.total_tokens,
        "created_at": result.created_at.isoformat() if result.created_at else None,
    }


class EvalService:
    """提示词评测集与执行的业务逻辑"""

    async def list_suites(
        self, db: AsyncSession, user_id: int, prompt_id: int | None = None
    ) -> list[dict[str, Any]]:
        """按提示词（可选）列出评测集"""
        query = (
            select(PromptEvalSuite)
            .options(selectinload(PromptEvalSuite.cases))
            .where(PromptEvalSuite.user_id == user_id)
            .order_by(PromptEvalSuite.id.desc())
        )
        if prompt_id is not None:
            query = query.where(PromptEvalSuite.prompt_id == prompt_id)
        result = await db.execute(query)
        return [_suite_out(suite) for suite in result.scalars().all()]

    async def create_suite(
        self, db: AsyncSession, user_id: int, data: EvalSuiteCreate
    ) -> dict[str, Any]:
        """创建评测集，同时写入用例"""
        await self._load_prompt(db, user_id, data.prompt_id)

        suite = PromptEvalSuite(
            user_id=user_id,
            prompt_id=data.prompt_id,
            name=data.name,
            description=data.description or "",
            judge_model=data.judge_model,
        )
        db.add(suite)
        await db.flush()

        for case in data.cases:
            db.add(
                PromptEvalCase(
                    suite_id=suite.id,
                    variables=json.dumps(case.variables, ensure_ascii=False),
                    expected_output=case.expected_output,
                    rubric=case.rubric,
                )
            )

        await db.commit()
        await db.refresh(suite)
        # 重新加载带用例的实例，避免依赖懒加载触发异步 IO
        suite = await self._get_suite(db, user_id, suite.id)
        return _suite_out(suite)

    async def delete_suite(self, db: AsyncSession, user_id: int, suite_id: int) -> None:
        """删除评测集（用例与结果随外键级联删除）"""
        suite = await self._get_suite(db, user_id, suite_id)
        await db.delete(suite)
        await db.commit()

    async def run(
        self, db: AsyncSession, user_id: int, suite_id: int, payload: EvalRunRequest
    ) -> dict[str, Any]:
        """执行评测：逐用例生成并打分，全部成功后一次性提交"""
        suite = await self._get_suite(db, user_id, suite_id)
        prompt = await self._load_prompt(db, user_id, suite.prompt_id)
        content, version = await self._resolve_content(db, prompt, payload.prompt_version_id)

        await ensure_quota(db, user_id)

        try:
            provider = get_chat_provider()
        except AIProviderError as exc:
            raise APIError(exc.code, str(exc)) from exc

        model = payload.model or settings.AI_CHAT_MODEL
        judge_model = suite.judge_model or model
        results: list[dict[str, Any]] = []
        scores: list[float] = []
        total_tokens = 0

        for case in sorted(suite.cases, key=lambda c: c.id or 0):
            variables = _load_json(case.variables, {})
            rendered_content = render_template(content, variables)

            try:
                answer = await provider.chat(
                    [{"role": "user", "content": rendered_content}],
                    model=model,
                    temperature=payload.temperature,
                )
            except AIProviderError as exc:
                # 生成阶段失败：放弃本轮全部结果，避免留下半套分数
                await db.rollback()
                raise APIError(exc.code, str(exc)) from exc

            score, reason, judge_usage, judge_latency = await self._judge(
                provider, judge_model, rendered_content, answer.content, case
            )
            usage = _merge_usage(answer.usage, judge_usage)
            total_tokens += usage.get("total_tokens", 0)

            record = PromptEvalResult(
                suite_id=suite.id,
                case_id=case.id,
                prompt_version_id=payload.prompt_version_id,
                model=model,
                output=answer.content,
                score=score,
                judge_reason=reason,
                latency_ms=answer.latency_ms + judge_latency,
                total_tokens=usage.get("total_tokens", 0),
            )
            db.add(record)
            results.append(
                {
                    "case_id": case.id,
                    "variables": variables,
                    "output": answer.content,
                    "score": score,
                    "judge_reason": reason,
                    "latency_ms": record.latency_ms,
                    "total_tokens": record.total_tokens,
                }
            )
            if score is not None:
                scores.append(score)

            await record_usage(
                db, user_id, "eval", model, usage, record.latency_ms
            )

        await db.commit()

        return {
            "suite_id": suite.id,
            "prompt_id": suite.prompt_id,
            "prompt_version_id": payload.prompt_version_id,
            "version_number": version.version_number if version else None,
            "model": model,
            "judge_model": judge_model,
            "case_count": len(results),
            "avg_score": round(sum(scores) / len(scores), 1) if scores else None,
            "total_tokens": total_tokens,
            "results": results,
        }

    async def list_results(
        self, db: AsyncSession, user_id: int, suite_id: int, limit: int = 50
    ) -> list[dict[str, Any]]:
        """最近的结果记录，按时间倒序"""
        await self._get_suite(db, user_id, suite_id)
        result = await db.execute(
            select(PromptEvalResult, PromptVersion.version_number)
            .outerjoin(PromptVersion, PromptVersion.id == PromptEvalResult.prompt_version_id)
            .where(PromptEvalResult.suite_id == suite_id)
            .order_by(PromptEvalResult.id.desc())
            .limit(limit)
        )
        return [_result_out(item, version_number) for item, version_number in result.all()]

    async def _get_suite(
        self, db: AsyncSession, user_id: int, suite_id: int
    ) -> PromptEvalSuite:
        """按归属加载评测集及其用例"""
        result = await db.execute(
            select(PromptEvalSuite)
            .options(selectinload(PromptEvalSuite.cases))
            .where(PromptEvalSuite.id == suite_id, PromptEvalSuite.user_id == user_id)
        )
        suite = result.scalar_one_or_none()
        if suite is None:
            raise APIError(ErrorCode.NOT_FOUND, "评测集不存在")
        return suite

    async def _load_prompt(
        self, db: AsyncSession, user_id: int, prompt_id: int
    ) -> Prompt:
        """按归属加载提示词"""
        result = await db.execute(
            select(Prompt).where(Prompt.id == prompt_id, Prompt.user_id == user_id)
        )
        prompt = result.scalar_one_or_none()
        if prompt is None:
            raise APIError(ErrorCode.PROMPT_NOT_FOUND, "提示词不存在")
        return prompt

    async def _resolve_content(
        self, db: AsyncSession, prompt: Prompt, version_id: int | None
    ) -> tuple[str, PromptVersion | None]:
        """取当前正文或指定历史版本正文"""
        if version_id is None:
            return prompt.content or "", None
        result = await db.execute(
            select(PromptVersion).where(
                PromptVersion.id == version_id, PromptVersion.prompt_id == prompt.id
            )
        )
        version = result.scalar_one_or_none()
        if version is None:
            raise APIError(ErrorCode.VERSION_NOT_FOUND, "版本不存在")
        return version.content or "", version

    async def _judge(
        self,
        provider: OpenAICompatibleProvider,
        judge_model: str,
        rendered: str,
        output: str,
        case: PromptEvalCase,
    ) -> tuple[float | None, str, dict[str, int], int]:
        """调用评委模型打分；无评分依据时只记录输出"""
        if not case.rubric and not case.expected_output:
            return None, "未设置评分要点，仅记录输出", {}, 0

        payload = (
            f"【提示词】\n{rendered[:2000]}\n\n"
            f"【期望输出】\n{case.expected_output or '（未提供）'}\n\n"
            f"【评分要点】\n{case.rubric or '（未提供）'}\n\n"
            f"【实际输出】\n{output[:4000]}"
        )
        try:
            judged = await provider.chat(
                [
                    {"role": "system", "content": JUDGE_SYSTEM},
                    {"role": "user", "content": payload},
                ],
                model=judge_model,
                temperature=0,
            )
        except AIProviderError as exc:
            logger.warning("评委模型调用失败：%s", exc)
            return None, f"评审 AI 调用失败：{exc}", {}, 0

        score, reason = _parse_judge(judged.content)
        return score, reason, judged.usage, judged.latency_ms


def _merge_usage(*items: dict[str, int]) -> dict[str, int]:
    """合并多个模型调用的用量"""
    merged: dict[str, int] = {}
    for item in items:
        for key, value in (item or {}).items():
            merged[key] = merged.get(key, 0) + int(value or 0)
    return merged


EVAL_SERVICE = EvalService()
