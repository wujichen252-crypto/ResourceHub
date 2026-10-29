"""AI 智能体身份层路由：人格、记忆与主动消息"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.response import orm_to_dict, success_response
from app.models.user import User
from app.schemas.agent import (
    AgentMemoryCreate,
    AgentMemoryExtractRequest,
    AgentMemoryOut,
    AgentMemoryUpdate,
    AgentProfileCreate,
    AgentProfileOut,
    AgentProfileUpdate,
    AgentProactiveMessageOut,
)
from app.services.ai.memory_service import MemoryService
from app.services.ai.persona_service import PersonaService
from app.services.ai.proactive_service import ProactiveService

router = APIRouter(tags=["AI 智能体"])
persona_service = PersonaService()
memory_service = MemoryService()
proactive_service = ProactiveService()


@router.get("/profiles")
async def list_profiles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出当前用户的智能体人格"""
    profiles = await persona_service.list_profiles(db, current_user.id)
    return success_response(
        data={
            "items": [
                AgentProfileOut.model_validate(orm_to_dict(item)).model_dump()
                for item in profiles
            ]
        },
        msg="获取人格列表成功",
    )


@router.post("/profiles", status_code=201)
async def create_profile(
    payload: AgentProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建智能体人格；首个自动成为默认"""
    profile = await persona_service.create(db, current_user.id, payload)
    return success_response(
        data=AgentProfileOut.model_validate(orm_to_dict(profile)).model_dump(),
        msg="创建人格成功",
        code=201,
    )


@router.put("/profiles/{profile_id}")
async def update_profile(
    profile_id: int,
    payload: AgentProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新人格"""
    profile = await persona_service.update(db, current_user.id, profile_id, payload)
    return success_response(
        data=AgentProfileOut.model_validate(orm_to_dict(profile)).model_dump(),
        msg="更新人格成功",
    )


@router.put("/profiles/{profile_id}/activate")
async def activate_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """把指定人格设为当前默认"""
    profile = await persona_service.activate(db, current_user.id, profile_id)
    return success_response(
        data=AgentProfileOut.model_validate(orm_to_dict(profile)).model_dump(),
        msg="已切换人格",
    )


@router.delete("/profiles/{profile_id}")
async def delete_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除人格"""
    await persona_service.delete(db, current_user.id, profile_id)
    return success_response(data=None, msg="删除人格成功")


@router.get("/memories")
async def list_memories(
    memory_type: str | None = Query(default=None),
    keyword: str | None = Query(default=None, max_length=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出长期记忆"""
    memories = await memory_service.list_memories(
        db, current_user.id, memory_type, keyword
    )
    return success_response(
        data={
            "items": [
                AgentMemoryOut.model_validate(orm_to_dict(item)).model_dump()
                for item in memories
            ],
            "total": len(memories),
        },
        msg="获取记忆列表成功",
    )


@router.post("/memories", status_code=201)
async def create_memory(
    payload: AgentMemoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """手动新增一条记忆"""
    memory = await memory_service.create_manual(db, current_user.id, payload)
    return success_response(
        data=AgentMemoryOut.model_validate(orm_to_dict(memory)).model_dump(),
        msg="已记住",
        code=201,
    )


@router.post("/memories/extract")
async def extract_memories(
    payload: AgentMemoryExtractRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """手动触发一次记忆抽取（演示用）"""
    result = await memory_service.extract_from_conversation(
        db, current_user.id, payload.conversation_id
    )
    return success_response(data=result, msg="记忆抽取完成")


@router.delete("/memories")
async def clear_memories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """清空当前用户的全部记忆"""
    deleted = await memory_service.clear(db, current_user.id)
    return success_response(data={"deleted": deleted}, msg="已清空记忆")


@router.put("/memories/{memory_id}")
async def update_memory(
    memory_id: int,
    payload: AgentMemoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新记忆"""
    memory = await memory_service.update(db, current_user.id, memory_id, payload)
    return success_response(
        data=AgentMemoryOut.model_validate(orm_to_dict(memory)).model_dump(),
        msg="更新记忆成功",
    )


@router.delete("/memories/{memory_id}")
async def delete_memory(
    memory_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除单条记忆"""
    await memory_service.delete(db, current_user.id, memory_id)
    return success_response(data=None, msg="删除记忆成功")


@router.get("/proactive/messages")
async def list_proactive_messages(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出主动消息"""
    messages = await proactive_service.list_messages(
        db, current_user.id, status, limit
    )
    return success_response(
        data={
            "items": [
                AgentProactiveMessageOut.model_validate(orm_to_dict(item)).model_dump()
                for item in messages
            ]
        },
        msg="获取主动消息成功",
    )


@router.put("/proactive/messages/{message_id}/read")
async def mark_proactive_read(
    message_id: int,
    status: str = Query(default="read", pattern="^(read|dismissed)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """把主动消息标记为已读或忽略"""
    message = await proactive_service.mark_read(db, current_user.id, message_id, status)
    return success_response(
        data=AgentProactiveMessageOut.model_validate(orm_to_dict(message)).model_dump(),
        msg="消息状态已更新",
    )


@router.post("/proactive/scan")
async def scan_proactive(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """手动触发一次主动扫描（演示用）"""
    result = await proactive_service.scan(db, current_user.id)
    return success_response(data=result.model_dump(), msg="主动扫描完成")
