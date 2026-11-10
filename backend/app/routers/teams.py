from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.response import success_response
from app.models.user import User
from app.schemas.team import (
    TeamCreate,
    TeamInviteOut,
    TeamJoinRequest,
    TeamMemberOut,
    TeamMemberRoleUpdate,
    TeamOut,
    TeamUpdate,
)
from app.services.team_service import TeamService

router = APIRouter(tags=["团队空间"])
service = TeamService()


@router.get("")
async def list_teams(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    teams = await service.list_my_teams(db, current_user.id)
    items = [TeamOut.model_validate(team).model_dump() for team in teams]
    return success_response(data=items, msg="获取团队列表成功")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_team(
    data: TeamCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    team = await service.create_team(db, current_user.id, data)
    return success_response(
        data=TeamOut.model_validate(team).model_dump(), msg="创建团队成功", code=201
    )


# 静态路径必须声明在 /{team_id} 之前，否则 "join" 会被当作路径参数解析
@router.post("/join")
async def join_team(
    data: TeamJoinRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    team = await service.join_by_code(db, current_user.id, data.invite_code)
    return success_response(
        data=TeamOut.model_validate(team).model_dump(), msg="加入团队成功"
    )


@router.get("/{team_id}")
async def get_team(
    team_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    team = await service.get_team(db, team_id, current_user.id)
    return success_response(
        data=TeamOut.model_validate(team).model_dump(), msg="获取团队详情成功"
    )


@router.put("/{team_id}")
async def update_team(
    team_id: int,
    data: TeamUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    team = await service.update_team(db, team_id, current_user.id, data)
    return success_response(
        data=TeamOut.model_validate(team).model_dump(), msg="更新团队成功"
    )


@router.delete("/{team_id}")
async def delete_team(
    team_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await service.delete_team(db, team_id, current_user.id)
    return success_response(msg="删除团队成功")


@router.post("/{team_id}/invite/regenerate")
async def regenerate_invite(
    team_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    code = await service.regenerate_invite(db, team_id, current_user.id)
    return success_response(
        data=TeamInviteOut(invite_code=code).model_dump(), msg="邀请码已重置"
    )


@router.post("/{team_id}/leave")
async def leave_team(
    team_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await service.leave_team(db, team_id, current_user.id)
    return success_response(msg="已退出团队")


@router.get("/{team_id}/members")
async def list_members(
    team_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    members = await service.list_members(db, team_id, current_user.id)
    items = [TeamMemberOut.model_validate(member).model_dump() for member in members]
    return success_response(data=items, msg="获取团队成员成功")


@router.put("/{team_id}/members/{user_id}")
async def update_member_role(
    team_id: int,
    user_id: int,
    data: TeamMemberRoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    member = await service.update_member_role(
        db, team_id, current_user.id, user_id, data.role
    )
    return success_response(
        data=TeamMemberOut.model_validate(member).model_dump(), msg="成员角色已更新"
    )


@router.delete("/{team_id}/members/{user_id}")
async def remove_member(
    team_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await service.remove_member(db, team_id, current_user.id, user_id)
    return success_response(msg="已移除该成员")
