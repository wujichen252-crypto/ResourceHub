"""AI 成本与效果看板聚合服务（知识资产 ROI）

设计对齐 stats_service：
- 只读聚合，日期分桶在 Python 端完成，保证 SQLite（开发/测试）与 MySQL（生产）行为一致
- 金额折算在读取时进行（模型单价可变，token 流水保持中立），未计价模型不计入金额
- 脏数据（citations 解析失败等）跳过，不影响整体统计
"""
import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ai import (
    AIUsageLog,
    AIMessage,
    AIConversation,
    NoteChunk,
    PromptEvalResult,
    PromptEvalSuite,
    PromptOptimizationRun,
)
from app.models.note import Note
from app.models.prompt import Prompt, PromptUsageLog

ROI_WINDOWS = (7, 30, 90)      # 允许的时间窗（天），白名单防任意值扫全表
TREND_DAYS = 30                # 默认趋势窗口
CITATION_WEIGHT = 10.0         # ROI 评分：单次 AI 引用权重
COST_UNIT = 1000.0             # ROI 评分：索引成本按千 token 折算
HIGH_YIELD_CITATIONS = 3       # 引用 ≥ 3 次 → 高产出
COST_HEAVY_TOKENS = 3000       # 未被引用且索引 token ≥ 该值 → 高耗低效

SCENE_LABELS = {
    "chat": "对话问答",
    "agent": "智能体",
    "embedding": "向量化索引",
    "eval": "提示词评测",
    "optimize": "提示词优化",
    "inline": "笔记内联",
    "memory": "记忆抽取",
    "proactive": "主动关怀",
}


def _as_date(value: datetime | date | None) -> date | None:
    if value is None:
        return None
    return value.date() if isinstance(value, datetime) else value


def _cost(model: str | None, prompt_tokens: int, completion_tokens: int) -> float | None:
    """按单价表折算金额（元）；模型未配置单价返回 None"""
    price = settings.ai_model_prices.get(model or "")
    if price is None:
        return None
    return (prompt_tokens * price["input"] + completion_tokens * price["output"]) / 1000.0


class RoiService:
    # ── 总览 ─────────────────────────────────────────
    async def get_summary(self, db: AsyncSession, user_id: int, days: int = 30) -> dict:
        start = datetime.combine(date.today() - timedelta(days=days - 1), datetime.min.time())
        rows = (await db.execute(
            select(
                AIUsageLog.scene,
                AIUsageLog.model,
                AIUsageLog.prompt_tokens,
                AIUsageLog.completion_tokens,
                AIUsageLog.total_tokens,
                AIUsageLog.latency_ms,
                AIUsageLog.success,
            ).where(
                AIUsageLog.user_id == user_id,
                AIUsageLog.created_at >= start,
            )
        )).all()

        total_tokens = 0
        total_calls = len(rows)
        ok_calls = 0
        latency_sum = 0
        cost_total = 0.0
        unpriced_tokens = 0
        by_scene: dict[str, dict] = defaultdict(lambda: {"calls": 0, "tokens": 0, "cost": 0.0})
        by_model: dict[str, dict] = defaultdict(lambda: {"calls": 0, "tokens": 0, "cost": 0.0})

        for scene, model, ptok, ctok, ttok, latency, success in rows:
            total_tokens += ttok
            latency_sum += latency
            if success:
                ok_calls += 1
            cost = _cost(model, ptok, ctok)
            if cost is None:
                unpriced_tokens += ttok
            else:
                cost_total += cost
            bucket_s = by_scene[scene]
            bucket_s["calls"] += 1
            bucket_s["tokens"] += ttok
            if cost is not None:
                bucket_s["cost"] += cost
            if model:
                bucket_m = by_model[model]
                bucket_m["calls"] += 1
                bucket_m["tokens"] += ttok
                if cost is not None:
                    bucket_m["cost"] += cost

        # 当日配额水位（复用 usage.today_tokens 的口径）
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        quota_used = int((await db.execute(
            select(func.coalesce(func.sum(AIUsageLog.total_tokens), 0)).where(
                AIUsageLog.user_id == user_id,
                AIUsageLog.created_at >= today,
            )
        )).scalar() or 0)

        return {
            "days": days,
            "total_tokens": total_tokens,
            "total_calls": total_calls,
            "success_rate": round(ok_calls / total_calls, 4) if total_calls else 1.0,
            "avg_latency_ms": latency_sum // total_calls if total_calls else 0,
            "cost_total": round(cost_total, 4),
            "unpriced_tokens": unpriced_tokens,
            "by_scene": [
                {"scene": s, **v} for s, v in
                sorted(by_scene.items(), key=lambda kv: kv[1]["tokens"], reverse=True)
            ],
            "by_model": [
                {"model": m, **v} for m, v in
                sorted(by_model.items(), key=lambda kv: kv[1]["tokens"], reverse=True)
            ],
            "quota_used_today": quota_used,
            "quota_limit": settings.AI_DAILY_TOKEN_QUOTA,
        }

    # ── 逐日趋势 ─────────────────────────────────────
    async def get_trend(self, db: AsyncSession, user_id: int, days: int = TREND_DAYS) -> dict:
        start_date = date.today() - timedelta(days=days - 1)
        start = datetime.combine(start_date, datetime.min.time())
        rows = (await db.execute(
            select(
                AIUsageLog.created_at,
                AIUsageLog.scene,
                AIUsageLog.model,
                AIUsageLog.prompt_tokens,
                AIUsageLog.completion_tokens,
                AIUsageLog.total_tokens,
                AIUsageLog.success,
            ).where(
                AIUsageLog.user_id == user_id,
                AIUsageLog.created_at >= start,
            )
        )).all()

        points: dict[date, dict] = {}
        for created_at, scene, model, ptok, ctok, ttok, success in rows:
            d = _as_date(created_at)
            if d is None or d < start_date:
                continue
            p = points.setdefault(d, {
                "calls": 0, "tokens": 0, "cost": 0.0, "failures": 0, "scenes": defaultdict(int),
            })
            p["calls"] += 1
            p["tokens"] += ttok
            if not success:
                p["failures"] += 1
            p["scenes"][scene] += ttok
            cost = _cost(model, ptok, ctok)
            if cost is not None:
                p["cost"] += cost

        return {
            "days": days,
            "points": [
                {
                    "date": (start_date + timedelta(days=i)).isoformat(),
                    "calls": points[start_date + timedelta(days=i)]["calls"],
                    "tokens": points[start_date + timedelta(days=i)]["tokens"],
                    "cost": round(points[start_date + timedelta(days=i)]["cost"], 4),
                    "failures": points[start_date + timedelta(days=i)]["failures"],
                    "scenes": dict(points[start_date + timedelta(days=i)]["scenes"]),
                }
                if (start_date + timedelta(days=i)) in points
                else {
                    "date": (start_date + timedelta(days=i)).isoformat(),
                    "calls": 0, "tokens": 0, "cost": 0.0, "failures": 0, "scenes": {},
                }
                for i in range(days)
            ],
        }

    # ── 笔记级 ROI ───────────────────────────────────
    async def get_notes_roi(self, db: AsyncSession, user_id: int, days: int = 30) -> list[dict]:
        start = datetime.combine(date.today() - timedelta(days=days - 1), datetime.min.time())

        # 1) 引用次数：解析 assistant 消息的 citations JSON，按 note_id 计数
        cite_rows = (await db.execute(
            select(AIMessage.citations)
            .join(AIConversation, AIMessage.conversation_id == AIConversation.id)
            .where(
                AIConversation.user_id == user_id,
                AIMessage.role == "assistant",
                AIMessage.citations.is_not(None),
                AIMessage.created_at >= start,
            )
        )).scalars().all()
        citations: Counter[int] = Counter()
        for raw in cite_rows:
            try:
                items = json.loads(raw)
            except (ValueError, TypeError):
                continue
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict) and isinstance(item.get("note_id"), int):
                    citations[item["note_id"]] += 1

        # 2) 索引成本：该笔记 chunk token 总数 × embedding 输入单价
        chunk_rows = (await db.execute(
            select(NoteChunk.note_id, func.sum(NoteChunk.token_count))
            .where(NoteChunk.user_id == user_id)
            .group_by(NoteChunk.note_id)
        )).all()
        index_tokens: dict[int, int] = {nid: int(tok or 0) for nid, tok in chunk_rows}

        emb_price = settings.ai_model_prices.get(settings.AI_EMBEDDING_MODEL)

        # 3) 参与比对的笔记池：有引用或有索引的笔记（避免全量笔记扫标题）
        note_ids = set(citations) | set(index_tokens)
        titles: dict[int, str] = {}
        if note_ids:
            note_rows = (await db.execute(
                select(Note.id, Note.title).where(
                    Note.user_id == user_id,
                    Note.id.in_(note_ids),
                )
            )).all()
            titles = {nid: title for nid, title in note_rows}

        items: list[dict] = []
        for nid in note_ids:
            r = citations.get(nid, 0)
            c = index_tokens.get(nid, 0)
            title = titles.get(nid, f"笔记 #{nid}")
            index_cost = (c / 1000.0 * emb_price["input"]) if emb_price else None
            # ROI 评分：引用收益 − 索引成本（成本以千 token 为单位折算进评分）
            roi_score = round(r * CITATION_WEIGHT - c / COST_UNIT, 2)
            if r >= HIGH_YIELD_CITATIONS:
                grade = "high_yield"
            elif r > 0:
                grade = "normal"
            elif c == 0:
                grade = "unindexed"
            elif c >= COST_HEAVY_TOKENS:
                grade = "cost_heavy"
            else:
                grade = "sleeping"
            items.append({
                "note_id": nid,
                "title": title,
                "citations": r,
                "index_tokens": c,
                "index_cost": round(index_cost, 4) if index_cost is not None else None,
                "grade": grade,
                "roi_score": roi_score,
            })
        items.sort(key=lambda x: x["roi_score"], reverse=True)
        return items

    # ── 提示词级 ROI ─────────────────────────────────
    async def get_prompts_roi(self, db: AsyncSession, user_id: int) -> list[dict]:
        # 1) 使用频次
        usage_rows = (await db.execute(
            select(PromptUsageLog.prompt_id, func.count())
            .where(PromptUsageLog.user_id == user_id)
            .group_by(PromptUsageLog.prompt_id)
        )).all()
        usage: dict[int, int] = {pid: int(cnt) for pid, cnt in usage_rows}

        # 2) 最近一次评测得分（suite → prompt_id）
        score_rows = (await db.execute(
            select(PromptEvalSuite.prompt_id, PromptEvalResult.score, PromptEvalResult.created_at)
            .join(PromptEvalResult, PromptEvalResult.suite_id == PromptEvalSuite.id)
            .where(PromptEvalSuite.user_id == user_id)
            .order_by(PromptEvalResult.created_at.desc())
        )).all()
        quality: dict[int, float] = {}
        for pid, score, _created in score_rows:
            if pid not in quality and score is not None:
                quality[pid] = float(score)

        # 3) 优化投入（optimize 场景按 prompt_id 归集）
        opt_rows = (await db.execute(
            select(
                AIUsageLog.prompt_id,
                AIUsageLog.model,
                func.sum(AIUsageLog.prompt_tokens),
                func.sum(AIUsageLog.completion_tokens),
            )
            .where(
                AIUsageLog.user_id == user_id,
                AIUsageLog.scene == "optimize",
                AIUsageLog.prompt_id.is_not(None),
            )
            .group_by(AIUsageLog.prompt_id, AIUsageLog.model)
        )).all()
        opt_tokens: dict[int, int] = defaultdict(int)
        opt_cost: dict[int, float] = defaultdict(float)
        for pid, model, ptok, ctok in opt_rows:
            opt_tokens[pid] += int(ptok or 0) + int(ctok or 0)
            cost = _cost(model, int(ptok or 0), int(ctok or 0))
            if cost is not None:
                opt_cost[pid] += cost

        # 4) 最近一次已完成优化会话的提分
        run_rows = (await db.execute(
            select(
                PromptOptimizationRun.prompt_id,
                PromptOptimizationRun.baseline_score,
                PromptOptimizationRun.candidate_score,
                PromptOptimizationRun.created_at,
            )
            .where(
                PromptOptimizationRun.user_id == user_id,
                PromptOptimizationRun.status == "completed",
            )
            .order_by(PromptOptimizationRun.created_at.desc())
        )).all()
        gains: dict[int, float] = {}
        for pid, base, cand, _created in run_rows:
            if pid not in gains and base is not None and cand is not None:
                gains[pid] = round(float(cand) - float(base), 1)

        # 5) 参与比对的提示词池
        prompt_ids = set(usage) | set(opt_tokens)
        titles: dict[int, str] = {}
        if prompt_ids:
            prompt_rows = (await db.execute(
                select(Prompt.id, Prompt.title).where(
                    Prompt.user_id == user_id,
                    Prompt.id.in_(prompt_ids),
                )
            )).all()
            titles = {pid: title for pid, title in prompt_rows}

        items: list[dict] = []
        for pid in prompt_ids:
            used = usage.get(pid, 0)
            score = quality.get(pid)
            invested = opt_tokens.get(pid, 0)
            # ROI 评分：使用次数 × 质量分 ÷ (1 + 优化投入千 token 数)；未评测按 0 分参与
            roi_score = round(used * (score or 0.0) / (1 + invested / COST_UNIT), 2)
            items.append({
                "prompt_id": pid,
                "title": titles.get(pid, f"提示词 #{pid}"),
                "usage_count": used,
                "quality_score": score,
                "optimize_tokens": invested,
                "optimize_cost": round(opt_cost.get(pid, 0.0), 4) if pid in opt_cost else None,
                "score_gain": gains.get(pid),
                "roi_score": roi_score,
            })
        items.sort(key=lambda x: x["roi_score"], reverse=True)
        return items

    # ── 场景四象限 ───────────────────────────────────
    async def get_scene_quadrant(self, db: AsyncSession, user_id: int, days: int = 30) -> list[dict]:
        start = datetime.combine(date.today() - timedelta(days=days - 1), datetime.min.time())
        rows = (await db.execute(
            select(
                AIUsageLog.scene,
                func.count(),
                func.sum(AIUsageLog.total_tokens),
                func.sum(AIUsageLog.latency_ms),
            ).where(
                AIUsageLog.user_id == user_id,
                AIUsageLog.created_at >= start,
            ).group_by(AIUsageLog.scene)
        )).all()

        items: list[dict] = []
        for scene, calls, tokens, latency_sum in rows:
            calls = int(calls)
            tokens = int(tokens or 0)
            items.append({
                "scene": scene,
                "calls": calls,
                "tokens": tokens,
                "cost": 0.0,  # 场景金额在路由层按模型明细补齐
                "avg_latency_ms": int(latency_sum or 0) // calls if calls else 0,
            })
        return items

    async def _scene_costs(self, db: AsyncSession, user_id: int, days: int) -> dict[str, float]:
        """按场景聚合已计价金额（供四象限 cost 字段）"""
        start = datetime.combine(date.today() - timedelta(days=days - 1), datetime.min.time())
        rows = (await db.execute(
            select(
                AIUsageLog.scene,
                AIUsageLog.model,
                func.sum(AIUsageLog.prompt_tokens),
                func.sum(AIUsageLog.completion_tokens),
            ).where(
                AIUsageLog.user_id == user_id,
                AIUsageLog.created_at >= start,
            ).group_by(AIUsageLog.scene, AIUsageLog.model)
        )).all()
        costs: dict[str, float] = defaultdict(float)
        for scene, model, ptok, ctok in rows:
            cost = _cost(model, int(ptok or 0), int(ctok or 0))
            if cost is not None:
                costs[scene] += cost
        return dict(costs)
