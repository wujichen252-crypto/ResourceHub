"""人格服务：智能体的身份、语气与边界

设计取舍：
- 人格只影响系统提示，不参与检索，避免身份设定污染知识依据。
- 同一用户只允许一个默认人格；激活新人格时在同一事务内取消旧的默认标记。
- 未配置人格时返回内置兜底人格，保证新旧用户开箱即用。
"""

from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode
from app.core.response import APIError
from app.models.agent import AgentProfile
from app.schemas.agent import AgentProfileCreate, AgentProfileUpdate


@dataclass(slots=True)
class Persona:
    """注入用的轻量人格视图，不依赖 ORM 生命周期"""

    name: str
    persona: str
    tone: str
    expertise: str | None = None
    boundaries: str | None = None
    greeting: str | None = None


DEFAULT_PERSONA = Persona(
    name="知识助手",
    persona="你的个人知识搭档，帮你梳理笔记、回答问题、推进目标",
    tone="严谨",
    greeting="我是你的知识搭档，问我任何你笔记里的问题。",
)

_TONE_HINTS = {
    "严谨": "回答严谨、有依据，先给结论再给依据，避免夸张和空泛表述",
    "轻松": "语气轻松自然，像朋友聊天，但不要牺牲准确性",
    "激励": "语气积极，适度鼓励，但不要空洞打气或过度承诺",
}


def _coerce_profile(profile: AgentProfile) -> Persona:
    """ORM 行转注入视图"""
    return Persona(
        name=profile.name,
        persona=profile.persona,
        tone=profile.tone,
        expertise=profile.expertise,
        boundaries=profile.boundaries,
        greeting=profile.greeting,
    )


def build_persona_prompt(persona: Persona) -> str:
    """把人格设定转成系统提示段

    只描述身份与表达方式，不提供事实依据；事实仍必须来自笔记或记忆上下文。
    """
    lines = [
        f"你的身份是「{persona.name}」。",
        f"角色定位：{persona.persona}",
        f"语气风格：{_TONE_HINTS.get(persona.tone, _TONE_HINTS['严谨'])}。",
    ]
    if persona.expertise:
        lines.append(f"专业领域：{persona.expertise}。")
    if persona.boundaries:
        lines.append(f"必须遵守的边界：{persona.boundaries}。")
    lines.append("请始终以这个身份作答，保持称呼、语气与边界一致。")
    return "\n".join(lines)


class PersonaService:
    """人格 CRUD 与激活"""

    async def get_active(self, db: AsyncSession, user_id: int) -> Persona:
        """取当前默认人格；没有配置时返回内置兜底"""
        result = await db.execute(
            select(AgentProfile)
            .where(AgentProfile.user_id == user_id, AgentProfile.is_default.is_(True))
            .limit(1)
        )
        profile = result.scalar_one_or_none()
        return _coerce_profile(profile) if profile else DEFAULT_PERSONA

    async def get_profile(
        self, db: AsyncSession, user_id: int, profile_id: int
    ) -> AgentProfile:
        """按归属加载人格，不存在时返回 7007"""
        result = await db.execute(
            select(AgentProfile).where(
                AgentProfile.id == profile_id, AgentProfile.user_id == user_id
            )
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            raise APIError(ErrorCode.AGENT_PROFILE_NOT_FOUND, "智能体人格不存在")
        return profile

    async def list_profiles(self, db: AsyncSession, user_id: int) -> list[AgentProfile]:
        """列出全部人格，默认人格排在最前"""
        result = await db.execute(
            select(AgentProfile)
            .where(AgentProfile.user_id == user_id)
            .order_by(AgentProfile.is_default.desc(), AgentProfile.created_at.asc())
        )
        return list(result.scalars().all())

    async def create(
        self, db: AsyncSession, user_id: int, payload: AgentProfileCreate
    ) -> AgentProfile:
        """创建人格；首个创建的人格自动成为默认"""
        existing = await db.execute(
            select(AgentProfile.id).where(AgentProfile.user_id == user_id).limit(1)
        )
        has_profile = existing.scalar_one_or_none() is not None
        make_default = payload.is_default or not has_profile
        if make_default:
            await self._clear_default(db, user_id)

        profile = AgentProfile(
            user_id=user_id,
            name=payload.name.strip(),
            persona=payload.persona.strip(),
            tone=payload.tone,
            expertise=(payload.expertise or "").strip() or None,
            boundaries=(payload.boundaries or "").strip() or None,
            greeting=(payload.greeting or "").strip() or None,
            is_default=make_default,
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        return profile

    async def update(
        self,
        db: AsyncSession,
        user_id: int,
        profile_id: int,
        payload: AgentProfileUpdate,
    ) -> AgentProfile:
        """更新人格；设为默认时取消其他默认标记"""
        profile = await self.get_profile(db, user_id, profile_id)
        data = payload.model_dump(exclude_unset=True)

        if data.get("is_default") is True:
            await self._clear_default(db, user_id, exclude_id=profile_id)
        for field in ("name", "persona", "expertise", "boundaries", "greeting"):
            if field in data:
                value = data[field]
                data[field] = value.strip() if isinstance(value, str) else value
                if data[field] == "":
                    data[field] = None
        for field, value in data.items():
            setattr(profile, field, value)
        await db.commit()
        await db.refresh(profile)
        return profile

    async def activate(
        self, db: AsyncSession, user_id: int, profile_id: int
    ) -> AgentProfile:
        """把指定人格设为当前默认"""
        profile = await self.get_profile(db, user_id, profile_id)
        await self._clear_default(db, user_id, exclude_id=profile_id)
        profile.is_default = True
        await db.commit()
        await db.refresh(profile)
        return profile

    async def delete(self, db: AsyncSession, user_id: int, profile_id: int) -> None:
        """删除人格；若删的是默认人格，自动把最早创建的一条提升为默认"""
        profile = await self.get_profile(db, user_id, profile_id)
        was_default = profile.is_default
        await db.delete(profile)
        await db.flush()
        if was_default:
            result = await db.execute(
                select(AgentProfile)
                .where(AgentProfile.user_id == user_id)
                .order_by(AgentProfile.created_at.asc())
                .limit(1)
            )
            next_profile = result.scalar_one_or_none()
            if next_profile is not None:
                next_profile.is_default = True
        await db.commit()

    @staticmethod
    async def _clear_default(
        db: AsyncSession, user_id: int, exclude_id: int | None = None
    ) -> None:
        """取消当前用户的默认标记"""
        statement = (
            update(AgentProfile)
            .where(AgentProfile.user_id == user_id, AgentProfile.is_default.is_(True))
            .values(is_default=False)
        )
        if exclude_id is not None:
            statement = statement.where(AgentProfile.id != exclude_id)
        await db.execute(statement)
