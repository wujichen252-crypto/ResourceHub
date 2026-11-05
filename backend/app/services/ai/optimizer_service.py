"""提示词自动优化器：评测闭环的"分析 → 改写"一环

流程（每轮四步）：
1. 基线评测（首轮才有）：对基线内容跑一遍评测集
2. 诊断改写：低分用例的输出 + 评委理由 → LLM 生成改进候选（结构化 JSON）
3. 候选评测：对候选内容用同一套用例、同一个评委模型重新打分
4. 对比报告：逐用例分差落库，进入 awaiting_review 等用户决策

用户决策：采纳（落新版本）/ 再优化一轮 / 放弃。AI 只建议，采纳永远由人触发。
所有模型调用记入用量表并受每日配额约束；候选丢失变量占位符时本轮作废（防漂移）。
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.errors import ErrorCode
from app.core.response import APIError
from app.models.ai import PromptEvalSuite, PromptOptimizationRound, PromptOptimizationRun
from app.models.prompt import Prompt, PromptVersion
from app.schemas.ai import OptimizationStartRequest
from app.services.ai.eval_service import EVAL_SERVICE
from app.services.ai.provider import AIProviderError, get_chat_provider
from app.services.ai.usage import ensure_quota, record_usage

logger = logging.getLogger(__name__)

# 运行中的会话超过该时长视为进程重启遗留，标记失败
STALE_RUNNING_MINUTES = 15

OPTIMIZE_SYSTEM = (
    "你是资深的提示词工程师。用户会给你一个提示词原文，以及它在评测集中表现不佳的用例："
    "变量取值、模型实际输出、评委扣分理由。请诊断问题并输出改进后的提示词。\n"
    "硬性要求：\n"
    "1. 必须保留原文的全部 {{变量}} 占位符，不得增删改名，不得改变原文的结构语义；\n"
    "2. 只做针对性改进：根据扣分理由补充约束、明确格式要求、消除歧义；\n"
    "3. 不要输出与提示词无关的内容。\n"
    "只返回一个 JSON 对象，格式为："
    '{"analysis": "不超过 120 字的问题诊断", "improved_content": "改进后的完整提示词", '
    '"changelog": "不超过 60 字的改动说明"}'
)


def _extract_variables(content: str | None) -> set[str]:
    """提取提示词中的 {{变量}} 占位符集合"""
    return set(re.findall(r"\{\{(\w+)\}\}", content or ""))


def _parse_optimizer_json(text: str) -> dict[str, str]:
    """解析诊断改写输出；解析失败抛业务异常，由调用方落 failed 状态"""
    raw = (text or "").strip()
    matched = re.search(r"\{.*\}", raw, re.S)
    if matched:
        try:
            data = json.loads(matched.group(0))
            improved = str(data.get("improved_content") or "").strip()
            if improved:
                return {
                    "analysis": str(data.get("analysis") or "").strip(),
                    "improved_content": improved,
                    "changelog": str(data.get("changelog") or "").strip()[:500],
                }
        except json.JSONDecodeError:
            pass
    raise APIError(ErrorCode.AI_PROVIDER_ERROR, "优化模型未返回合法的 JSON 结果，请重试")


def _run_out(run: PromptOptimizationRun) -> dict[str, Any]:
    """优化会话输出结构"""
    return {
        "id": run.id,
        "prompt_id": run.prompt_id,
        "suite_id": run.suite_id,
        "status": run.status,
        "round_number": run.round_number,
        "max_rounds": run.max_rounds,
        "score_threshold": run.score_threshold,
        "baseline_version_id": run.baseline_version_id,
        "baseline_content": run.baseline_content,
        "baseline_score": run.baseline_score,
        "candidate_content": run.candidate_content,
        "candidate_score": run.candidate_score,
        "candidate_version_id": run.candidate_version_id,
        "analysis": run.analysis,
        "changelog": run.changelog,
        "total_tokens": run.total_tokens,
        "error_message": run.error_message,
        "baseline_detail": json.loads(run.baseline_detail) if run.baseline_detail else None,
        "candidate_detail": json.loads(run.candidate_detail) if run.candidate_detail else None,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "updated_at": run.updated_at.isoformat() if run.updated_at else None,
    }


def _round_out(item: PromptOptimizationRound) -> dict[str, Any]:
    """单轮历史输出结构"""
    return {
        "id": item.id,
        "round_number": item.round_number,
        "status": item.status,
        "candidate_content": item.candidate_content,
        "candidate_score": item.candidate_score,
        "reference_score": item.reference_score,
        "analysis": item.analysis,
        "changelog": item.changelog,
        "snapshot": json.loads(item.snapshot) if item.snapshot else None,
        "total_tokens": item.total_tokens,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


class OptimizerService:
    """提示词自动优化器的业务逻辑与后台任务编排"""

    # ── 会话生命周期 ──

    async def start_run(
        self, db: AsyncSession, user_id: int, payload: OptimizationStartRequest
    ) -> dict[str, Any]:
        """创建优化会话并启动第一轮后台任务"""
        prompt = await self._load_prompt(db, user_id, payload.prompt_id)
        suite = await self._load_suite(db, user_id, payload.suite_id)
        if suite.prompt_id != prompt.id:
            raise APIError(ErrorCode.BAD_REQUEST, "评测集不属于该提示词")

        baseline_content, baseline_version_id = await self._resolve_baseline(
            db, prompt, payload.prompt_version_id
        )

        run = PromptOptimizationRun(
            user_id=user_id,
            prompt_id=prompt.id,
            suite_id=suite.id,
            status="running",
            round_number=0,
            max_rounds=payload.max_rounds,
            score_threshold=payload.score_threshold,
            temperature=payload.temperature,
            baseline_version_id=baseline_version_id,
            baseline_content=baseline_content,
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)

        self._spawn_round_task(run.id, user_id)
        return _run_out(run)

    async def iterate(self, db: AsyncSession, user_id: int, run_id: int) -> dict[str, Any]:
        """在 awaiting_review 状态下继续下一轮"""
        run = await self._load_run(db, user_id, run_id)
        if run.status != "awaiting_review":
            raise APIError(ErrorCode.BAD_REQUEST, "当前状态不能继续迭代")
        if run.round_number >= run.max_rounds:
            raise APIError(ErrorCode.BAD_REQUEST, "已达最大优化轮数")
        run.status = "running"
        await db.commit()
        await db.refresh(run)

        self._spawn_round_task(run.id, user_id)
        return _run_out(run)

    async def accept(self, db: AsyncSession, user_id: int, run_id: int) -> dict[str, Any]:
        """采纳候选：写入新版本（changelog 作 commit message），正文同步更新"""
        run = await self._load_run(db, user_id, run_id)
        if run.status != "awaiting_review" or not run.candidate_content:
            raise APIError(ErrorCode.BAD_REQUEST, "当前没有可采纳的候选结果")

        prompt = await self._load_prompt(db, user_id, run.prompt_id)

        # 快照当前正文，再写入候选内容（与 restore_version 的保护思路一致）
        max_ver = await db.execute(
            select(PromptVersion.version_number)
            .where(PromptVersion.prompt_id == prompt.id)
            .order_by(PromptVersion.version_number.desc())
            .limit(1)
        )
        next_ver = (max_ver.scalar() or 0) + 1
        version = PromptVersion(
            prompt_id=prompt.id,
            version_number=next_ver,
            title=prompt.title,
            description=prompt.description,
            content=prompt.content,
            variables=prompt.variables,
            tags=prompt.tags,
            message="自动优化前的快照",
            branch_name="main",
        )
        db.add(version)

        prompt.content = run.candidate_content
        new_version = PromptVersion(
            prompt_id=prompt.id,
            version_number=next_ver + 1,
            title=prompt.title,
            description=prompt.description,
            content=run.candidate_content,
            variables=prompt.variables,
            tags=prompt.tags,
            message=run.changelog or "AI 自动优化",
            branch_name="main",
        )
        db.add(new_version)

        run.candidate_version_id = new_version.id
        run.status = "completed"
        await db.commit()
        await db.refresh(run)
        await db.refresh(new_version)

        out = _run_out(run)
        out["new_version"] = {
            "id": new_version.id,
            "version_number": new_version.version_number,
            "message": new_version.message,
        }
        return out

    async def cancel(self, db: AsyncSession, user_id: int, run_id: int) -> dict[str, Any]:
        """取消会话；running 状态下由后台任务协作中止"""
        run = await self._load_run(db, user_id, run_id)
        if run.status in ("completed", "cancelled"):
            raise APIError(ErrorCode.BAD_REQUEST, "会话已结束")
        run.status = "cancelled"
        await db.commit()
        await db.refresh(run)
        return _run_out(run)

    async def get_status(self, db: AsyncSession, user_id: int, run_id: int) -> dict[str, Any]:
        """轮询会话状态；顺带回收进程重启遗留的 running 会话"""
        await self._reap_stale(db)
        run = await self._load_run(db, user_id, run_id)
        return _run_out(run)

    async def list_runs(
        self,
        db: AsyncSession,
        user_id: int,
        prompt_id: int | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """当前用户的优化会话列表（时间倒序）；前端用于恢复进行中的会话"""
        query = (
            select(PromptOptimizationRun)
            .where(PromptOptimizationRun.user_id == user_id)
            .order_by(PromptOptimizationRun.id.desc())
            .limit(limit)
        )
        if prompt_id is not None:
            query = query.where(PromptOptimizationRun.prompt_id == prompt_id)
        result = await db.execute(query)
        return [_run_out(item) for item in result.scalars().all()]

    async def list_rounds(
        self, db: AsyncSession, user_id: int, run_id: int
    ) -> list[dict[str, Any]]:
        """会话的轮次历史（按轮次正序）"""
        run = await self._load_run(db, user_id, run_id)
        result = await db.execute(
            select(PromptOptimizationRound)
            .where(PromptOptimizationRound.run_id == run.id)
            .order_by(PromptOptimizationRound.round_number)
        )
        return [_round_out(item) for item in result.scalars().all()]

    # ── 后台流水线 ──

    def _spawn_round_task(self, run_id: int, user_id: int) -> None:
        """启动后台轮次任务；异常只落日志，状态由任务自身落库"""
        task = asyncio.create_task(self._execute_round(run_id, user_id))
        task.add_done_callback(_log_task_exception)

    async def _execute_round(self, run_id: int, user_id: int) -> None:
        """后台执行一轮优化；使用独立会话，异常统一落 failed 状态"""
        async with SessionLocal() as db:
            try:
                await self._run_round(db, run_id, user_id)
            except APIError as exc:
                await self._mark_failed(db, run_id, str(exc))
            except AIProviderError as exc:
                await self._mark_failed(db, run_id, str(exc))
            except Exception:
                logger.exception("自动优化轮次执行失败 run_id=%s", run_id)
                await self._mark_failed(db, run_id, "优化过程中出现内部错误，请重试")

    async def _run_round(self, db: AsyncSession, run_id: int, user_id: int) -> None:
        run = await self._get_run(db, run_id)
        if run.status != "running":  # 用户已取消
            return

        # 配额前置检查：不足直接 failed，避免烧到一半被截断
        await ensure_quota(db, user_id)
        if run.status != "running":
            return

        try:
            provider = get_chat_provider()
        except AIProviderError as exc:
            raise APIError(exc.code, str(exc)) from exc

        suite = await self._load_suite(db, user_id, run.suite_id)

        # 第 1 步：基线评测（仅首轮）
        if run.round_number == 0:
            baseline = await EVAL_SERVICE.run_content(
                db,
                user_id,
                suite,
                run.baseline_content or "",
                prompt_version_id=run.baseline_version_id,
                temperature=run.temperature,
            )
            await db.refresh(run)  # 取消状态由其他会话写入，需刷新后可见
            if run.status != "running":
                return
            run.baseline_score = baseline.get("avg_score")
            run.baseline_detail = json.dumps(
                baseline.get("results", []), ensure_ascii=False
            )
            run.total_tokens += baseline.get("total_tokens", 0)
            await db.commit()

        # 上一轮的候选明细优先作为参照；字段以 JSON 文本落库，需先反序列化
        reference_score = run.candidate_score or run.baseline_score
        detail_raw = run.candidate_detail or run.baseline_detail
        try:
            reference_detail = json.loads(detail_raw) if detail_raw else []
        except json.JSONDecodeError:
            reference_detail = []
        if not isinstance(reference_detail, list):
            reference_detail = []

        # 第 2 步：诊断改写
        low_cases = self._pick_low_cases(reference_detail or [], run.score_threshold)
        if not low_cases:
            # 没有低分用例可诊断：无需继续
            await self._finish_round(
                db,
                run,
                round_status="skipped",
                analysis="所有用例已达到目标分数，没有需要优化的用例",
                reference_score=reference_score,
            )
            return

        diagnose_usage, parsed = await self._diagnose(
            provider, run, low_cases
        )
        await db.refresh(run)
        if run.status != "running":
            return

        candidate_content = parsed["improved_content"]

        # 第 3 步：变量一致性校验（防漂移）
        base_vars = _extract_variables(run.baseline_content)
        cand_vars = _extract_variables(candidate_content)
        if base_vars != cand_vars:
            await record_usage(
                user_id, "optimize", settings.AI_FAST_MODEL, diagnose_usage, 0,
                prompt_id=run.prompt_id,
            )
            await self._finish_round(
                db,
                run,
                round_status="skipped",
                analysis=(
                    "候选提示词的变量占位符与原文不一致（"
                    f"原文 {sorted(base_vars)} vs 候选 {sorted(cand_vars)}），本轮已作废。"
                    "可以再优化一轮。"
                ),
                reference_score=reference_score,
                extra_tokens=diagnose_usage.get("total_tokens", 0),
            )
            return

        # 第 4 步：候选评测（同一套用例、同一个评委模型）
        candidate = await EVAL_SERVICE.run_content(
            db,
            user_id,
            suite,
            candidate_content,
            temperature=run.temperature,
        )
        await db.refresh(run)
        if run.status != "running":
            return

        await record_usage(
            user_id, "optimize", settings.AI_FAST_MODEL, diagnose_usage, 0,
            prompt_id=run.prompt_id,
        )

        snapshot = self._build_snapshot(reference_detail or [], candidate.get("results", []))
        round_tokens = diagnose_usage.get("total_tokens", 0) + candidate.get("total_tokens", 0)

        await self._finish_round(
            db,
            run,
            round_status="completed",
            analysis=parsed["analysis"],
            changelog=parsed["changelog"],
            candidate_content=candidate_content,
            candidate_score=candidate.get("avg_score"),
            candidate_detail=json.dumps(candidate.get("results", []), ensure_ascii=False),
            reference_score=reference_score,
            snapshot=snapshot,
            extra_tokens=round_tokens,
        )

    # ── 单轮内部的原子步骤 ──

    async def _diagnose(
        self,
        provider: Any,
        run: PromptOptimizationRun,
        low_cases: list[dict[str, Any]],
    ) -> tuple[dict[str, int], dict[str, str]]:
        """调用优化模型诊断并改写，返回（用量, 解析结果）"""
        cases_text = ""
        for i, item in enumerate(low_cases[:5], start=1):
            variables = item.get("variables") or {}
            cases_text += (
                f"\n【用例 {i}】变量取值：{json.dumps(variables, ensure_ascii=False)}\n"
                f"实际输出：{(item.get('output') or '')[:1500]}\n"
                f"评委扣分理由：{(item.get('judge_reason') or '')[:300]}\n"
            )
        payload = (
            f"【提示词原文】\n{run.candidate_content or run.baseline_content or ''}\n\n"
            f"【基线得分】{run.candidate_score or run.baseline_score or '未评测'}\n"
            f"【表现不佳的用例】{cases_text}"
        )
        judged = await provider.chat(
            [
                {"role": "system", "content": OPTIMIZE_SYSTEM},
                {"role": "user", "content": payload[:8000]},
            ],
            model=settings.AI_FAST_MODEL,
            temperature=run.temperature,
        )
        return judged.usage or {}, _parse_optimizer_json(judged.content)

    def _pick_low_cases(
        self, detail: list[dict[str, Any]], threshold: float
    ) -> list[dict[str, Any]]:
        """从评测明细中挑出低于阈值的用例"""
        return [
            item
            for item in detail
            if item.get("score") is not None and float(item["score"]) < threshold
        ]

    def _build_snapshot(
        self, reference_detail: list[dict[str, Any]], candidate_detail: list[dict[str, Any]]
    ) -> str:
        """按 case_id 拼接逐用例对比快照"""
        ref_map = {item.get("case_id"): item for item in reference_detail}
        snapshot: list[dict[str, Any]] = []
        for cand in candidate_detail:
            ref = ref_map.get(cand.get("case_id"), {})
            ref_score = ref.get("score")
            cand_score = cand.get("score")
            delta = (
                round(float(cand_score) - float(ref_score), 1)
                if cand_score is not None and ref_score is not None
                else None
            )
            snapshot.append(
                {
                    "case_id": cand.get("case_id"),
                    "variables": cand.get("variables"),
                    "reference_score": ref_score,
                    "candidate_score": cand_score,
                    "delta": delta,
                    "reference_reason": ref.get("judge_reason"),
                    "candidate_reason": cand.get("judge_reason"),
                }
            )
        return json.dumps(snapshot, ensure_ascii=False)

    async def _finish_round(
        self,
        db: AsyncSession,
        run: PromptOptimizationRun,
        *,
        round_status: str,
        analysis: str,
        reference_score: float | None = None,
        changelog: str | None = None,
        candidate_content: str | None = None,
        candidate_score: float | None = None,
        candidate_detail: str | None = None,
        snapshot: str | None = None,
        extra_tokens: int = 0,
    ) -> None:
        """落一轮结果：写轮次历史 + 更新会话状态为 awaiting_review"""
        next_round = run.round_number + 1
        db.add(
            PromptOptimizationRound(
                run_id=run.id,
                round_number=next_round,
                status=round_status,
                candidate_content=candidate_content,
                candidate_score=candidate_score,
                reference_score=reference_score,
                analysis=analysis,
                changelog=changelog,
                snapshot=snapshot,
                total_tokens=extra_tokens,
            )
        )
        run.round_number = next_round
        run.status = "awaiting_review"
        run.analysis = analysis
        run.changelog = changelog
        run.candidate_content = candidate_content
        run.candidate_score = candidate_score
        run.candidate_detail = candidate_detail
        run.total_tokens += extra_tokens
        await db.commit()
        await db.refresh(run)

    async def _mark_failed(self, db: AsyncSession, run_id: int, message: str) -> None:
        """把会话置为 failed；会话已被取消/删除时静默跳过"""
        try:
            # 异常路径下事务可能已处于待回滚状态，先回滚保证状态写入可靠
            await db.rollback()
            run = await self._get_run(db, run_id)
        except APIError:
            return
        if run.status in ("cancelled", "completed"):
            return
        run.status = "failed"
        run.error_message = message[:500]
        await db.commit()

    # ── 加载与守护 ──

    async def _reap_stale(self, db: AsyncSession) -> None:
        """回收超时的 running 会话（进程重启遗留）"""
        deadline = datetime.now() - timedelta(minutes=STALE_RUNNING_MINUTES)
        result = await db.execute(
            select(PromptOptimizationRun).where(
                PromptOptimizationRun.status == "running",
                PromptOptimizationRun.updated_at < deadline,
            )
        )
        stale_runs = result.scalars().all()
        for run in stale_runs:
            run.status = "failed"
            run.error_message = "优化任务超时中断，请重新发起"
        if stale_runs:
            await db.commit()

    async def _get_run(self, db: AsyncSession, run_id: int) -> PromptOptimizationRun:
        result = await db.execute(
            select(PromptOptimizationRun).where(PromptOptimizationRun.id == run_id)
        )
        run = result.scalar_one_or_none()
        if run is None:
            raise APIError(ErrorCode.NOT_FOUND, "优化会话不存在")
        return run

    async def _load_run(self, db: AsyncSession, user_id: int, run_id: int) -> PromptOptimizationRun:
        run = await self._get_run(db, run_id)
        if run.user_id != user_id:
            raise APIError(ErrorCode.NOT_FOUND, "优化会话不存在")
        return run

    async def _load_prompt(self, db: AsyncSession, user_id: int, prompt_id: int) -> Prompt:
        result = await db.execute(
            select(Prompt).where(Prompt.id == prompt_id, Prompt.user_id == user_id)
        )
        prompt = result.scalar_one_or_none()
        if prompt is None:
            raise APIError(ErrorCode.PROMPT_NOT_FOUND, "提示词不存在")
        return prompt

    async def _load_suite(
        self, db: AsyncSession, user_id: int, suite_id: int
    ) -> PromptEvalSuite:
        result = await db.execute(
            select(PromptEvalSuite)
            .options(selectinload(PromptEvalSuite.cases))
            .where(PromptEvalSuite.id == suite_id, PromptEvalSuite.user_id == user_id)
        )
        suite = result.scalar_one_or_none()
        if suite is None:
            raise APIError(ErrorCode.NOT_FOUND, "评测集不存在")
        return suite

    async def _resolve_baseline(
        self, db: AsyncSession, prompt: Prompt, version_id: int | None
    ) -> tuple[str, int | None]:
        """基线内容：指定版本或当前正文"""
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
        return version.content or "", version.id


def _log_task_exception(task: asyncio.Task) -> None:
    """后台任务兜底：未处理的异常不能无声消失"""
    if not task.cancelled() and task.exception() is not None:
        logger.error("自动优化后台任务异常：%s", task.exception())


OPTIMIZER_SERVICE = OptimizerService()
