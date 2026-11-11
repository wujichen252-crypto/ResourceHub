"""团队知识库服务：团队 CRUD、成员与角色管理、资源访问鉴权"""

import secrets

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode
from app.core.response import orm_to_dict
from app.models.note import Note
from app.models.prompt import Prompt
from app.models.team import Team, TeamMember
from app.models.user import User
from app.schemas.team import TeamCreate, TeamUpdate

ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_MEMBER = "member"

# 去掉易混淆的 I/O/0/1，便于口头传达邀请码
_INVITE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_ROLE_ORDER = {ROLE_OWNER: 0, ROLE_ADMIN: 1, ROLE_MEMBER: 2}


def generate_invite_code() -> str:
    """生成 8 位大写邀请码"""
    return "".join(secrets.choice(_INVITE_ALPHABET) for _ in range(8))


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"code": ErrorCode.TEAM_NOT_FOUND, "message": "团队不存在"},
    )


def _forbidden(message: str = "仅团队成员可以访问该资源") -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={"code": ErrorCode.TEAM_FORBIDDEN, "message": message},
    )


class TeamService:
    """团队知识库核心逻辑：成员关系即权限边界"""

    async def _counts(self, db: AsyncSession, team_id: int) -> dict[str, int]:
        """统计团队内的成员数与资源数，供列表与详情展示"""
        member_count = await db.scalar(
            select(func.count(TeamMember.id)).where(TeamMember.team_id == team_id)
        )
        note_count = await db.scalar(
            select(func.count(Note.id)).where(Note.team_id == team_id)
        )
        prompt_count = await db.scalar(
            select(func.count(Prompt.id)).where(Prompt.team_id == team_id)
        )
        return {
            "member_count": int(member_count or 0),
            "note_count": int(note_count or 0),
            "prompt_count": int(prompt_count or 0),
        }

    async def _unique_invite_code(self, db: AsyncSession) -> str:
        """生成未被占用的邀请码，最多重试 5 次"""
        for _ in range(5):
            code = generate_invite_code()
            exists = await db.scalar(select(Team.id).where(Team.invite_code == code))
            if exists is None:
                return code
        raise HTTPException(
            status_code=500,
            detail={"code": ErrorCode.INTERNAL_ERROR, "message": "邀请码生成失败，请重试"},
        )

    async def get_role(self, db: AsyncSession, team_id: int, user_id: int) -> str | None:
        """返回用户在团队中的角色，非成员返回 None"""
        return await db.scalar(
            select(TeamMember.role).where(
                TeamMember.team_id == team_id, TeamMember.user_id == user_id
            )
        )

    async def team_ids(self, db: AsyncSession, user_id: int) -> list[int]:
        """当前用户加入的全部团队 ID，供 AI 检索扩展知识范围"""
        result = await db.execute(
            select(TeamMember.team_id).where(TeamMember.user_id == user_id)
        )
        return list(result.scalars().all())

    async def is_member(self, db: AsyncSession, team_id: int, user_id: int) -> bool:
        return await self.get_role(db, team_id, user_id) is not None

    async def can_manage(self, db: AsyncSession, team_id: int, user_id: int) -> bool:
        """owner / admin 具备成员与团队设置的管理权限"""
        return await self.get_role(db, team_id, user_id) in (ROLE_OWNER, ROLE_ADMIN)

    async def list_my_teams(self, db: AsyncSession, user_id: int) -> list[dict]:
        # 相关子查询需显式 correlate(Team)，否则与 joins 里的 team_members 自动消解冲突
        member_count = (
            select(func.count(TeamMember.id))
            .where(TeamMember.team_id == Team.id)
            .correlate(Team)
            .scalar_subquery()
        )
        note_count = (
            select(func.count(Note.id))
            .where(Note.team_id == Team.id)
            .correlate(Team)
            .scalar_subquery()
        )
        prompt_count = (
            select(func.count(Prompt.id))
            .where(Prompt.team_id == Team.id)
            .correlate(Team)
            .scalar_subquery()
        )
        result = await db.execute(
            select(Team, TeamMember.role, member_count, note_count, prompt_count)
            .join(TeamMember, TeamMember.team_id == Team.id)
            .where(TeamMember.user_id == user_id)
            .order_by(Team.updated_at.desc())
        )
        return [
            {
                **orm_to_dict(team),
                "role": role,
                "member_count": int(mc or 0),
                "note_count": int(nc or 0),
                "prompt_count": int(pc or 0),
            }
            for team, role, mc, nc, pc in result.all()
        ]

    async def _get_team(self, db: AsyncSession, team_id: int) -> Team:
        team = await db.scalar(select(Team).where(Team.id == team_id))
        if team is None:
            raise _not_found()
        return team

    async def get_team(self, db: AsyncSession, team_id: int, user_id: int) -> dict:
        team = await self._get_team(db, team_id)
        role = await self.get_role(db, team_id, user_id)
        if role is None:
            raise _forbidden()
        return {**orm_to_dict(team), "role": role, **(await self._counts(db, team_id))}

    async def create_team(self, db: AsyncSession, user_id: int, data: TeamCreate) -> dict:
        team = Team(
            name=data.name.strip(),
            description=(data.description or "").strip() or None,
            owner_id=user_id,
            invite_code=await self._unique_invite_code(db),
        )
        db.add(team)
        await db.flush()
        db.add(TeamMember(team_id=team.id, user_id=user_id, role=ROLE_OWNER))
        await db.commit()
        await db.refresh(team)
        return {
            **orm_to_dict(team),
            "role": ROLE_OWNER,
            "member_count": 1,
            "note_count": 0,
            "prompt_count": 0,
        }

    async def update_team(
        self, db: AsyncSession, team_id: int, user_id: int, data: TeamUpdate
    ) -> dict:
        team = await self._get_team(db, team_id)
        if not await self.can_manage(db, team_id, user_id):
            raise _forbidden("仅团队管理员可以修改团队信息")
        if data.name is not None:
            team.name = data.name.strip()
        if data.description is not None:
            team.description = data.description.strip() or None
        await db.commit()
        await db.refresh(team)
        return await self.get_team(db, team_id, user_id)

    async def delete_team(self, db: AsyncSession, team_id: int, user_id: int) -> None:
        team = await self._get_team(db, team_id)
        if team.owner_id != user_id:
            raise _forbidden("仅团队创建者可以删除团队")
        # 显式把团队资源放回作者个人空间：SQLite 默认不启用外键级联，不能依赖 ON DELETE SET NULL
        await db.execute(update(Note).where(Note.team_id == team_id).values(team_id=None))
        await db.execute(update(Prompt).where(Prompt.team_id == team_id).values(team_id=None))
        await db.delete(team)
        await db.commit()

    async def regenerate_invite(self, db: AsyncSession, team_id: int, user_id: int) -> str:
        team = await self._get_team(db, team_id)
        if not await self.can_manage(db, team_id, user_id):
            raise _forbidden("仅团队管理员可以重置邀请码")
        team.invite_code = await self._unique_invite_code(db)
        await db.commit()
        return team.invite_code

    async def join_by_code(self, db: AsyncSession, user_id: int, invite_code: str) -> dict:
        code = invite_code.strip().upper()
        team = await db.scalar(select(Team).where(Team.invite_code == code))
        if team is None:
            raise HTTPException(
                status_code=400,
                detail={"code": ErrorCode.TEAM_INVITE_INVALID, "message": "邀请码无效"},
            )
        if await self.is_member(db, team.id, user_id):
            raise HTTPException(
                status_code=409,
                detail={"code": ErrorCode.TEAM_MEMBER_EXISTS, "message": "你已经是该团队成员"},
            )
        db.add(TeamMember(team_id=team.id, user_id=user_id, role=ROLE_MEMBER))
        await db.commit()
        return await self.get_team(db, team.id, user_id)

    async def list_members(self, db: AsyncSession, team_id: int, user_id: int) -> list[dict]:
        await self._get_team(db, team_id)
        if not await self.is_member(db, team_id, user_id):
            raise _forbidden()
        result = await db.execute(
            select(TeamMember, User)
            .join(User, User.id == TeamMember.user_id)
            .where(TeamMember.team_id == team_id)
        )
        rows = [
            {
                "id": member.id,
                "user_id": member.user_id,
                "username": account.username,
                "avatar": account.avatar,
                "role": member.role,
                "joined_at": member.joined_at,
            }
            for member, account in result.all()
        ]
        rows.sort(key=lambda item: (_ROLE_ORDER.get(item["role"], 9), item["user_id"]))
        return rows

    async def update_member_role(
        self, db: AsyncSession, team_id: int, user_id: int, target_user_id: int, role: str
    ) -> dict:
        team = await self._get_team(db, team_id)
        if team.owner_id != user_id:
            raise _forbidden("仅团队创建者可以调整成员角色")
        member = await db.scalar(
            select(TeamMember).where(
                TeamMember.team_id == team_id, TeamMember.user_id == target_user_id
            )
        )
        if member is None:
            raise HTTPException(
                status_code=404,
                detail={"code": ErrorCode.TEAM_MEMBER_NOT_FOUND, "message": "团队成员不存在"},
            )
        if member.role == ROLE_OWNER:
            raise _forbidden("不能修改团队创建者的角色")
        member.role = role
        await db.commit()
        members = await self.list_members(db, team_id, user_id)
        return next(item for item in members if item["user_id"] == target_user_id)

    async def remove_member(
        self, db: AsyncSession, team_id: int, user_id: int, target_user_id: int
    ) -> None:
        team = await self._get_team(db, team_id)
        operator_role = await self.get_role(db, team_id, user_id)
        if operator_role not in (ROLE_OWNER, ROLE_ADMIN):
            raise _forbidden("仅团队管理员可以移除成员")
        if target_user_id == team.owner_id:
            raise _forbidden("不能移除团队创建者")
        member = await db.scalar(
            select(TeamMember).where(
                TeamMember.team_id == team_id, TeamMember.user_id == target_user_id
            )
        )
        if member is None:
            raise HTTPException(
                status_code=404,
                detail={"code": ErrorCode.TEAM_MEMBER_NOT_FOUND, "message": "团队成员不存在"},
            )
        # 管理员之间平级，只有创建者可以移除管理员
        if member.role == ROLE_ADMIN and operator_role != ROLE_OWNER:
            raise _forbidden("管理员不能移除其他管理员")
        await db.delete(member)
        await db.commit()

    async def leave_team(self, db: AsyncSession, team_id: int, user_id: int) -> None:
        team = await self._get_team(db, team_id)
        if team.owner_id == user_id:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": ErrorCode.TEAM_OWNER_CANNOT_LEAVE,
                    "message": "团队创建者不能直接退出，请先删除团队",
                },
            )
        member = await db.scalar(
            select(TeamMember).where(
                TeamMember.team_id == team_id, TeamMember.user_id == user_id
            )
        )
        if member is None:
            raise _forbidden()
        await db.delete(member)
        await db.commit()

    async def assert_can_write_team_resource(
        self, db: AsyncSession, team_id: int | None, user_id: int
    ) -> None:
        """创建团队资源前校验成员身份；个人资源直接放行"""
        if team_id is None:
            return
        if not await self.is_member(db, team_id, user_id):
            raise _forbidden("只有团队成员才能在该团队中创建资源")

    async def assert_can_edit_resource(
        self, db: AsyncSession, user_id: int, owner_id: int, team_id: int | None
    ) -> None:
        """资源编辑权限：作者本人，或团队 owner/admin"""
        if owner_id == user_id:
            return
        if team_id is not None and await self.can_manage(db, team_id, user_id):
            return
        raise _forbidden("没有权限修改该资源")

    async def assert_can_read_resource(
        self, db: AsyncSession, user_id: int, owner_id: int, team_id: int | None
    ) -> bool:
        """资源读取权限：本人 → 团队资源看成员身份 → 否则返回 False"""
        if owner_id == user_id:
            return True
        if team_id is not None:
            return await self.is_member(db, team_id, user_id)
        return False
