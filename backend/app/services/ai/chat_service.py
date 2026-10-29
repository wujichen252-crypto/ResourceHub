"""RAG 问答服务：检索 → 引用 → 流式生成 → 留痕

对外只暴露 SSE 事件流，前端按事件协议增量渲染；
会话与消息落库，引用可回溯到具体笔记片段。
"""

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import ErrorCode
from app.models.ai import AIConversation, AIMessage
from app.models.user import User
from app.schemas.ai import ChatRequest
from app.services.ai.chunking import estimate_tokens
from app.services.ai.memory_service import MemoryService, build_memory_context, schedule_extraction
from app.services.ai.persona_service import PersonaService, build_persona_prompt
from app.services.ai.provider import AIProviderError, get_chat_provider
from app.services.ai.retrieval import retrieve
from app.services.ai.safety import (
    SYSTEM_GUARD,
    detect_prompt_injection,
    mask_pii,
    refusal_text,
    wrap_untrusted_context,
)
from app.services.ai.sse import sse_event
from app.services.ai.usage import ensure_quota, record_usage

logger = logging.getLogger(__name__)


class ChatService:
    """RAG 流式问答"""

    def __init__(self) -> None:
        self.persona_service = PersonaService()
        self.memory_service = MemoryService()

    async def stream(
        self, db: AsyncSession, user: User, request: ChatRequest
    ) -> AsyncIterator[str]:
        """生成 SSE 事件流

        客户端断开时生成器会被取消，此时立刻回滚：已写入的会话消息会持有行锁，
        不清理会拖住后续同一用户的写入。
        """
        try:
            async for event in self._stream_events(db, user, request):
                yield event
        except (GeneratorExit, asyncio.CancelledError):
            await db.rollback()
            raise

    async def _stream_events(
        self, db: AsyncSession, user: User, request: ChatRequest
    ) -> AsyncIterator[str]:
        """真正的问答流程，由 stream 负责取消时的清理"""
        started = time.perf_counter()
        await ensure_quota(db, user.id)

        conversation = await self._prepare_conversation(db, user.id, request)
        model = request.model or settings.AI_CHAT_MODEL
        yield sse_event(
            "meta",
            {"conversation_id": conversation.id, "model": model, "use_rag": request.use_rag},
        )

        persona = await self.persona_service.get_active(db, user.id)
        persona_prompt = build_persona_prompt(persona)
        # 同一 AsyncSession 不能并发执行查询，记忆与笔记检索按顺序执行
        memories = await self.memory_service.retrieve(db, user.id, request.message)
        memory_context = build_memory_context(memories)

        hits = []
        if request.use_rag:
            hits = await retrieve(db, user.id, request.message, request.top_k)
            for index, hit in enumerate(hits, start=1):
                yield sse_event(
                    "citation",
                    {
                        "index": index,
                        "chunk_id": hit.chunk_id,
                        "note_id": hit.note_id,
                        "note_title": hit.note_title,
                        "snippet": mask_pii(hit.content[:200]),
                        "score": hit.score,
                    },
                )
                if detect_prompt_injection(hit.content):
                    logger.warning("检索片段命中注入特征 chunk=%s", hit.chunk_id)

        # 笔记与记忆都无依据时直接拒答，避免模型编造
        if request.use_rag and not hits and not memories:
            answer = refusal_text()
            yield sse_event("token", {"text": answer})
            await self._persist(db, conversation, request, answer, [], {"total_tokens": 0}, 0)
            yield sse_event(
                "done",
                {"conversation_id": conversation.id, "citations": 0, "usage": {"total_tokens": 0}},
            )
            return

        messages = self._build_messages(request, hits, persona_prompt, memory_context)
        answer_parts: list[str] = []
        usage: dict[str, int] = {}

        try:
            provider = get_chat_provider()
            async for event in provider.stream_chat(messages, model, request.temperature):
                if event.kind == "token":
                    answer_parts.append(event.text)
                    yield sse_event("token", {"text": event.text})
                elif event.kind == "done":
                    usage = event.usage
        except AIProviderError as exc:
            latency = int((time.perf_counter() - started) * 1000)
            await record_usage(
                db, user.id, "chat", model, usage, latency, success=False,
                error_code=str(exc.code),
            )
            await db.commit()
            yield sse_event("error", {"code": exc.code, "message": exc.message})
            return

        latency = int((time.perf_counter() - started) * 1000)
        answer = "".join(answer_parts)
        citations = [self._citation_payload(index, hit) for index, hit in enumerate(hits, start=1)]
        await self._persist(db, conversation, request, answer, citations, usage, latency)
        await record_usage(db, user.id, "chat", model, usage, latency)
        await db.commit()

        # 对话提交后再调度记忆抽取，失败不影响已经返回的回答
        schedule_extraction(user.id, conversation.id)

        yield sse_event(
            "done",
            {
                "conversation_id": conversation.id,
                "citations": len(citations),
                "usage": usage or {"total_tokens": estimate_tokens(answer)},
            },
        )

    async def _prepare_conversation(
        self, db: AsyncSession, user_id: int, request: ChatRequest
    ) -> AIConversation:
        """续聊则校验归属，新会话则创建"""
        if request.conversation_id:
            result = await db.execute(
                select(AIConversation).where(
                    AIConversation.id == request.conversation_id,
                    AIConversation.user_id == user_id,
                )
            )
            conversation = result.scalar_one_or_none()
            if conversation is not None:
                return conversation

        title = request.message.strip().replace("\n", " ")[:30] or "新对话"
        conversation = AIConversation(
            user_id=user_id, title=title, model=request.model or settings.AI_CHAT_MODEL
        )
        db.add(conversation)
        await db.flush()
        return conversation

    @staticmethod
    def _build_messages(
        request: ChatRequest,
        hits: list,
        persona_prompt: str | None = None,
        memory_context: str | None = None,
    ) -> list[dict[str, str]]:
        """组装系统提示、历史对话与检索上下文"""
        parts = [persona_prompt, SYSTEM_GUARD] if persona_prompt else [SYSTEM_GUARD]
        if memory_context:
            parts.append(memory_context)
        context = wrap_untrusted_context(hits)
        if context:
            parts.append(context)
        elif memory_context:
            parts.append(
                "本轮没有检索到笔记依据，但存在用户长期记忆。可以基于记忆回答，"
                "并说明信息来自记忆；不要编造笔记中没有的依据。"
            )
        else:
            # 用户主动关闭“仅基于笔记回答”时，明确允许使用通用知识，且不需要标注来源
            parts.append(
                "本轮没有检索到笔记依据，请直接用通用知识回答，"
                "并在开头说明这是通用知识、不是来自用户笔记；不要标注来源编号。"
            )
        messages: list[dict[str, str]] = [{"role": "system", "content": "\n\n".join(parts)}]
        for turn in request.history[-20:]:
            messages.append({"role": turn.role, "content": turn.content})
        messages.append({"role": "user", "content": request.message})
        return messages

    @staticmethod
    def _citation_payload(index: int, hit) -> dict:
        return {
            "index": index,
            "chunk_id": hit.chunk_id,
            "note_id": hit.note_id,
            "note_title": hit.note_title,
            "snippet": hit.content[:200],
            "score": hit.score,
        }

    async def _persist(
        self,
        db: AsyncSession,
        conversation: AIConversation,
        request: ChatRequest,
        answer: str,
        citations: list[dict],
        usage: dict[str, int],
        latency_ms: int,
    ) -> None:
        """落库用户消息与助手回复"""
        db.add(
            AIMessage(
                conversation_id=conversation.id,
                role="user",
                content=request.message,
                prompt_tokens=usage.get("prompt_tokens", 0),
            )
        )
        db.add(
            AIMessage(
                conversation_id=conversation.id,
                role="assistant",
                content=answer,
                citations=json.dumps(citations, ensure_ascii=False) if citations else None,
                completion_tokens=usage.get("completion_tokens", 0),
                latency_ms=latency_ms,
                model=request.model or settings.AI_CHAT_MODEL,
            )
        )
        conversation.message_count += 2
        await db.flush()
