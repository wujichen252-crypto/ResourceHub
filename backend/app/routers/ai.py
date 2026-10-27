"""AI 能力层路由：状态、索引、RAG 问答、Agent 运行与恢复"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.core.errors import ErrorCode
from app.core.response import APIError, success_response
from app.models.ai import AIConversation, AIMessage, NoteChunk
from app.models.note import Note
from app.models.user import User
from app.schemas.ai import (
    AgentResumeRequest,
    AgentRunRequest,
    ChatRequest,
    EvalRunRequest,
    EvalSuiteCreate,
    IndexRebuildRequest,
)
from app.services.ai.agent import AgentService
from app.services.ai.chat_service import ChatService
from app.services.ai.eval_service import EVAL_SERVICE
from app.services.ai.index_service import IndexService

router = APIRouter(tags=["AI 能力"])
chat_service = ChatService()
agent_service = AgentService()
index_service = IndexService()

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",  # 关闭 Nginx 缓冲，保证逐字输出
}


def _ensure_ai_ready() -> None:
    """未配置模型密钥时快速失败，避免前端收到半截 SSE"""
    if not settings.ai_configured:
        raise APIError(
            ErrorCode.AI_NOT_CONFIGURED,
            "AI 功能还没有启用，请在项目配置文件中填写 AI 服务密钥后再试",
        )


@router.get("/status")
async def ai_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI 能力层状态与索引概况"""
    note_count = await _scalar(
        db, select(func.count(Note.id)).where(Note.user_id == current_user.id)
    )
    chunk_count = await _scalar(
        db, select(func.count(NoteChunk.id)).where(NoteChunk.user_id == current_user.id)
    )
    indexed_note_count = await _scalar(
        db,
        select(func.count(func.distinct(NoteChunk.note_id))).where(
            NoteChunk.user_id == current_user.id
        ),
    )
    return success_response(
        data={
            "configured": settings.ai_configured,
            "chat_model": settings.AI_CHAT_MODEL,
            "embedding_model": settings.AI_EMBEDDING_MODEL,
            "embedding_dim": settings.AI_EMBEDDING_DIM,
            "note_count": note_count,
            "chunk_count": chunk_count,
            "indexed_note_count": indexed_note_count,
        },
        msg="获取 AI 状态成功",
    )


@router.post("/index/rebuild")
async def rebuild_index(
    payload: IndexRebuildRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """重建笔记索引；向量服务不可用时自动降级为关键词检索"""
    result = await index_service.rebuild(db, current_user.id, payload.note_ids)
    return success_response(data=result, msg=result["message"])


@router.post("/chat")
async def chat(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """RAG 流式问答（SSE）"""
    _ensure_ai_ready()
    return StreamingResponse(
        chat_service.stream(db, current_user, payload),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.post("/agent/run")
async def run_agent(
    payload: AgentRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Agent 任务执行（SSE，含工具调用轨迹）"""
    _ensure_ai_ready()
    return StreamingResponse(
        agent_service.stream(db, current_user, payload),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.post("/agent/resume")
async def resume_agent(
    payload: AgentResumeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """确认或拒绝挂起的写操作（SSE）"""
    _ensure_ai_ready()
    return StreamingResponse(
        agent_service.resume(db, current_user, payload),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.get("/conversations")
async def list_conversations(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """最近会话列表"""
    result = await db.execute(
        select(AIConversation)
        .where(AIConversation.user_id == current_user.id)
        .order_by(AIConversation.updated_at.desc())
        .limit(limit)
    )
    conversations = result.scalars().all()
    return success_response(
        data={
            "items": [
                {
                    "id": item.id,
                    "title": item.title,
                    "model": item.model,
                    "message_count": item.message_count,
                    "created_at": item.created_at,
                    "updated_at": item.updated_at,
                }
                for item in conversations
            ]
        },
        msg="获取会话列表成功",
    )


@router.get("/conversations/{conversation_id}/messages")
async def list_messages(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """会话消息（含引用与工具调用留档）"""
    owner = await db.execute(
        select(AIConversation.id).where(
            AIConversation.id == conversation_id,
            AIConversation.user_id == current_user.id,
        )
    )
    if owner.scalar_one_or_none() is None:
        raise APIError(ErrorCode.NOT_FOUND, "会话不存在")

    result = await db.execute(
        select(AIMessage)
        .where(AIMessage.conversation_id == conversation_id)
        .order_by(AIMessage.id)
    )
    messages = result.scalars().all()
    return success_response(
        data={
            "items": [
                {
                    "id": item.id,
                    "role": item.role,
                    "content": item.content,
                    "citations": item.citations,
                    "created_at": item.created_at,
                }
                for item in messages
            ]
        },
        msg="获取会话消息成功",
    )


@router.get("/eval/suites")
async def list_eval_suites(
    prompt_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """评测集列表（可按提示词过滤）"""
    items = await EVAL_SERVICE.list_suites(db, current_user.id, prompt_id)
    return success_response(data={"items": items}, msg="获取评测集成功")


@router.post("/eval/suites", status_code=201)
async def create_eval_suite(
    payload: EvalSuiteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建评测集（含评测用例）"""
    suite = await EVAL_SERVICE.create_suite(db, current_user.id, payload)
    return success_response(data=suite, msg="创建评测集成功", code=201)


@router.delete("/eval/suites/{suite_id}")
async def delete_eval_suite(
    suite_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除评测集"""
    await EVAL_SERVICE.delete_suite(db, current_user.id, suite_id)
    return success_response(data=None, msg="删除评测集成功")


@router.post("/eval/suites/{suite_id}/run")
async def run_eval_suite(
    suite_id: int,
    payload: EvalRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """执行评测：逐用例生成并由评委模型打分"""
    _ensure_ai_ready()
    result = await EVAL_SERVICE.run(db, current_user.id, suite_id, payload)
    return success_response(data=result, msg="评测完成")


@router.get("/eval/suites/{suite_id}/results")
async def list_eval_results(
    suite_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """评测结果历史（时间倒序）"""
    items = await EVAL_SERVICE.list_results(db, current_user.id, suite_id, limit)
    return success_response(data={"items": items}, msg="获取评测结果成功")


async def _scalar(db: AsyncSession, query) -> int:
    """执行计数查询"""
    result = await db.execute(query)
    return int(result.scalar() or 0)
