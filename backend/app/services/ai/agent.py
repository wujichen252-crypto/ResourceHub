"""Agent 编排：规划 → 工具调用 → 观察 → 继续，最多 N 步

安全设计：
- 只读工具直接执行；写工具（新建/更新笔记）默认挂起，等待用户确认
- 每次运行落库 ai_runs，步骤可回放，前端可展示完整执行轨迹
- 步数与 token 均受预算约束，避免死循环和额度失控
"""

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import ErrorCode
from app.models.ai import AIRun
from app.models.user import User
from app.schemas.ai import AgentResumeRequest, AgentRunRequest
from app.services.ai.provider import AIProviderError, get_chat_provider
from app.services.ai.memory_service import MemoryService, build_memory_context
from app.services.ai.persona_service import PersonaService, build_persona_prompt
from app.services.ai.sse import sse_event
from app.services.ai.tools import TOOL_REGISTRY, ToolContext
from app.services.ai.usage import ensure_quota, record_usage

logger = logging.getLogger(__name__)

AGENT_SYSTEM = """你是 ResourceHub 的个人知识 Agent，可以调用工具完成用户任务。
工作方式：
1. 先判断是否需要检索笔记（search_notes），再决定下一步
2. 一次只调用必要的工具，拿到结果后继续推理，不要重复调用相同参数
3. 新建/更新笔记属于写操作，系统会要求用户确认，不要假设已执行
4. 完成后用简体中文给出简洁的结论与执行摘要，不要输出工具调用细节"""


class AgentService:
    """Agent 运行与恢复"""

    def __init__(self) -> None:
        self.persona_service = PersonaService()
        self.memory_service = MemoryService()

    async def stream(
        self, db: AsyncSession, user: User, request: AgentRunRequest
    ) -> AsyncIterator[str]:
        """执行 Agent 任务并流式输出轨迹

        客户端断开（关页面、刷新、切网络）时生成器会被取消。此时必须立刻回滚事务：
        已经 flush 的 ai_runs/ai_messages 会一直持有行锁，拖住后续写入并引发 1205/1213。
        """
        try:
            async for event in self._stream_events(db, user, request):
                yield event
        except (GeneratorExit, asyncio.CancelledError):
            await db.rollback()
            raise

    async def _stream_events(
        self, db: AsyncSession, user: User, request: AgentRunRequest
    ) -> AsyncIterator[str]:
        """真正的执行流程，由 stream 负责取消时的清理"""
        await ensure_quota(db, user.id)
        provider = get_chat_provider()
        model = request.model or settings.AI_CHAT_MODEL
        max_steps = min(request.max_steps, settings.AI_AGENT_MAX_STEPS)

        run = AIRun(user_id=user.id, conversation_id=request.conversation_id, goal=request.goal)
        db.add(run)
        await db.flush()
        yield sse_event("meta", {"run_id": run.id, "model": model, "max_steps": max_steps})

        persona = await self.persona_service.get_active(db, user.id)
        persona_prompt = build_persona_prompt(persona)
        memories = await self.memory_service.retrieve(db, user.id, request.goal)
        memory_context = build_memory_context(memories)
        system_content = "\n\n".join(
            part for part in (persona_prompt, AGENT_SYSTEM, memory_context) if part
        )

        messages: list[dict] = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": request.goal},
        ]
        steps: list[dict] = []
        usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        started = time.perf_counter()

        for step in range(1, max_steps + 1):
            content_parts: list[str] = []
            tool_calls: list[dict] = []
            try:
                async for event in provider.stream_chat(
                    messages, model, 0.2, tools=TOOL_REGISTRY.specs()
                ):
                    if event.kind == "token":
                        content_parts.append(event.text)
                        yield sse_event("token", {"text": event.text})
                    elif event.kind == "tool_call":
                        tool_calls.append(event.tool_call)
                    elif event.kind == "done":
                        usage = _merge_usage(usage, event.usage)
            except AIProviderError as exc:
                await self._fail(db, run, steps, str(exc), started)
                yield sse_event("error", {"code": exc.code, "message": exc.message})
                return

            if not tool_calls:
                break

            messages.append(
                {
                    "role": "assistant",
                    "content": "".join(content_parts),
                    "tool_calls": tool_calls,
                }
            )
            for call in tool_calls:
                name = (call.get("function") or {}).get("name", "")
                arguments = (call.get("function") or {}).get("arguments", "{}")
                yield sse_event(
                    "tool_call",
                    {"step": step, "id": call.get("id"), "name": name, "arguments": arguments},
                )

                if TOOL_REGISTRY.is_write(name) and not request.confirm_write:
                    await self._suspend(db, run, steps, messages, call)
                    yield sse_event(
                        "awaiting_confirmation",
                        {
                            "run_id": run.id,
                            "tool": name,
                            "arguments": arguments,
                            "message": "该操作会修改你的笔记，请确认后继续",
                        },
                    )
                    return

                result = await TOOL_REGISTRY.execute(name, arguments, ToolContext(db, user.id))
                steps.append({"step": step, "tool": name, "arguments": arguments, "result": result[:500]})
                messages.append({"role": "tool", "tool_call_id": call.get("id"), "content": result})
                yield sse_event("tool_result", {"step": step, "name": name, "result": result[:500]})

        latency = int((time.perf_counter() - started) * 1000)
        run.status = "succeeded"
        run.steps = json.dumps(steps, ensure_ascii=False)
        run.step_count = len(steps)
        run.prompt_tokens = usage["prompt_tokens"]
        run.completion_tokens = usage["completion_tokens"]
        run.finished_at = datetime.now()
        await db.flush()
        await record_usage(db, user.id, "agent", model, usage, latency)
        await db.commit()
        yield sse_event("done", {"run_id": run.id, "steps": len(steps), "usage": usage})

    async def resume(
        self, db: AsyncSession, user: User, request: AgentResumeRequest
    ) -> AsyncIterator[str]:
        """确认（或拒绝）挂起的写操作，并继续生成结论"""
        result = await db.execute(
            select(AIRun).where(AIRun.id == request.run_id, AIRun.user_id == user.id)
        )
        run = result.scalar_one_or_none()
        if run is None or not run.pending_action:
            yield sse_event("error", {"code": ErrorCode.AI_RUN_NOT_FOUND, "message": "这次任务已结束或不存在，请重新发起"})
            return

        pending = json.loads(run.pending_action)
        call = pending.get("call", {})
        messages = pending.get("messages", [])
        if not request.approve:
            run.status = "cancelled"
            run.pending_action = None
            run.finished_at = datetime.now()
            await db.commit()
            yield sse_event("done", {"run_id": run.id, "cancelled": True})
            return

        name = (call.get("function") or {}).get("name", "")
        arguments = (call.get("function") or {}).get("arguments", "{}")
        tool_result = await TOOL_REGISTRY.execute(name, arguments, ToolContext(db, user.id))
        messages.append({"role": "tool", "tool_call_id": call.get("id"), "content": tool_result})
        yield sse_event("tool_result", {"run_id": run.id, "name": name, "result": tool_result[:500]})

        answer = await self._final_answer(messages, tool_result)
        run.status = "succeeded"
        run.pending_action = None
        run.finished_at = datetime.now()
        run.steps = json.dumps(
            [{"tool": name, "arguments": arguments, "result": tool_result[:500]}], ensure_ascii=False
        )
        run.step_count += 1
        await db.commit()
        yield sse_event("token", {"text": answer})
        yield sse_event("done", {"run_id": run.id, "approved": True})

    async def _final_answer(self, messages: list[dict], tool_result: str) -> str:
        """写操作完成后生成收尾说明"""
        provider = get_chat_provider()
        summary = messages + [
            {"role": "user", "content": "请用一两句话向用户说明刚刚执行的操作结果。"}
        ]
        try:
            result = await provider.chat(summary, settings.AI_CHAT_MODEL, 0.2, 500)
            return result.content or "操作已完成。"
        except AIProviderError:
            return f"操作已完成：{tool_result[:200]}"

    async def _suspend(
        self,
        db: AsyncSession,
        run: AIRun,
        steps: list[dict],
        messages: list[dict],
        call: dict,
    ) -> None:
        """挂起运行，持久化待确认动作与上下文"""
        run.status = "waiting_confirmation"
        run.steps = json.dumps(steps, ensure_ascii=False)
        run.step_count = len(steps)
        run.pending_action = json.dumps({"call": call, "messages": messages}, ensure_ascii=False)
        await db.commit()

    async def _fail(
        self, db: AsyncSession, run: AIRun, steps: list[dict], error: str, started: float
    ) -> None:
        """记录失败状态"""
        run.status = "failed"
        run.error = error[:500]
        run.steps = json.dumps(steps, ensure_ascii=False)
        run.finished_at = datetime.now()
        await db.flush()
        await record_usage(
            db, run.user_id, "agent", None, {}, int((time.perf_counter() - started) * 1000),
            success=False, error_code=str(ErrorCode.AI_PROVIDER_ERROR),
        )
        await db.commit()


def _merge_usage(total: dict[str, int], part: dict[str, int]) -> dict[str, int]:
    """累加多轮用量"""
    return {
        "prompt_tokens": total.get("prompt_tokens", 0) + part.get("prompt_tokens", 0),
        "completion_tokens": total.get("completion_tokens", 0) + part.get("completion_tokens", 0),
        "total_tokens": total.get("total_tokens", 0) + part.get("total_tokens", 0),
    }
