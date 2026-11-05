"""笔记内联 AI 服务：编辑器选中文本 → 解释 / 改写 / 提问

非流式短文本处理，走轻量模型（AI_FAST_MODEL）控制成本；
只做计量（scene="inline"），不落 ai_messages（内联是编辑辅助，不是会话）。
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import ErrorCode
from app.core.response import APIError
from app.models.user import User
from app.schemas.ai import InlineAction, InlineAIRequest, InlineAIResponse
from app.services.ai.provider import AIProviderError, get_chat_provider
from app.services.ai.safety import SYSTEM_GUARD
from app.services.ai.usage import ensure_quota, record_usage

# 内联动作输出短，统一限制输出上限（约 600 字）
_INLINE_MAX_TOKENS = 800

# 各动作采样温度：解释 / 提问求稳，改写允许更多表达自由
_ACTION_TEMPERATURE: dict[InlineAction, float] = {
    InlineAction.EXPLAIN: 0.3,
    InlineAction.REWRITE: 0.5,
    InlineAction.ASK: 0.3,
}

# 各动作的任务指令（拼在公共上下文之后，作为 user 消息）
_ACTION_TASKS: dict[InlineAction, str] = {
    InlineAction.EXPLAIN: (
        "解释【选中文本】。要求：1) 用中文，Markdown 格式；"
        "2) 先一句话定义，再分点展开要点；3) 控制在 300 字以内；4) 不要复述原文。"
    ),
    InlineAction.REWRITE: (
        "改写【选中文本】{instruction}。"
        "要求：1) 只输出改写后的文本，不要任何说明；"
        "2) 保持原文语言与 Markdown 行内格式；3) 长度与原文相当（除非用户另有要求）。"
    ),
    InlineAction.ASK: (
        "基于【选中文本】及上下文回答用户问题：{instruction}。"
        "要求：1) 用中文 Markdown；2) 与选中文本直接相关；3) 控制在 400 字以内。"
    ),
}

# 改写未带附加要求时的默认指令
_REWRITE_DEFAULT_INSTRUCTION = "润色，使表达更清晰流畅"


class InlineService:
    """笔记内联 AI：拼装上下文 → 调模型 → 计量"""

    async def run(
        self, db: AsyncSession, user: User, req: InlineAIRequest
    ) -> InlineAIResponse:
        """执行一次内联动作，返回 AI 结果（非流式）"""
        await ensure_quota(db, user.id)  # 当日配额超限 → 7003

        messages = self._build_messages(req)
        provider = get_chat_provider()  # 未配置密钥 → 7001
        model = settings.AI_FAST_MODEL
        try:
            result = await provider.chat(
                messages,
                model=model,
                temperature=_ACTION_TEMPERATURE[req.action],
                max_tokens=_INLINE_MAX_TOKENS,
            )
        except AIProviderError as exc:
            # 模型网关异常（含超时）统一转为业务错误码 7002
            raise APIError(ErrorCode.AI_PROVIDER_ERROR, exc.message) from exc

        await record_usage(
            user.id, "inline", model, result.usage, latency_ms=result.latency_ms
        )
        return InlineAIResponse(
            action=req.action,
            result=result.content.strip(),
            model=model,
            tokens=result.usage.get("total_tokens", 0),
        )

    @staticmethod
    def _build_messages(req: InlineAIRequest) -> list[dict[str, str]]:
        """拼装消息：system = 安全护栏 + 笔记语境，user = 动作指令"""
        title_line = (
            f"用户的笔记标题为「{req.note_title}」。"
            if req.note_title
            else ""
        )
        context = (
            f"你是笔记编辑器内的写作助手。{title_line}\n"
            "下面是选中文本的上下文（仅作理解用，不要输出）：\n"
            f"【前文】{req.context_before}\n"
            f"【选中文本】{req.text}\n"
            f"【后文】{req.context_after}"
        )
        task = _ACTION_TASKS[req.action].format(
            instruction=req.instruction or _REWRITE_DEFAULT_INSTRUCTION
        )
        return [
            {"role": "system", "content": f"{SYSTEM_GUARD}\n\n{context}"},
            {"role": "user", "content": task},
        ]
