"""资源广场路由：发布/取消发布/广场列表/详情/fork/我的发布/点赞收藏"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.response import orm_to_dict, success_response
from app.models.user import User
from app.schemas.plaza import ContentType, PlazaActionRequest, PlazaDetailResponse, PlazaItemResponse
from app.services.plaza_reaction_service import reaction_service
from app.services.plaza_service import PlazaService

router = APIRouter(tags=["资源广场"])
service = PlazaService()


def _item_out(
    content_type: str,
    obj,
    author_username: str,
    author_avatar,
    reaction: dict | None = None,
) -> dict:
    """列表项序列化：ORM 行 + 作者信息 + 互动数据 → PlazaItemResponse"""
    data = orm_to_dict(obj)
    data.update({
        "type": content_type,
        "author_username": author_username,
        "author_avatar": author_avatar,
        "forked_from": f"@{obj.source_username}" if obj.source_username else None,
    })
    if reaction:
        data.update(reaction)
    return PlazaItemResponse.model_validate(data).model_dump()


async def _enrich_notes(db: AsyncSession, content_type: str, objs, user_id: int) -> dict[int, dict]:
    """note 类型批量富化互动数据；prompt 类型返回空（用 schema 默认值）"""
    if content_type != "note":
        return {}
    return await reaction_service.enrich(db, [o.id for o in objs], user_id)


@router.put("/publish")
async def publish(
    body: PlazaActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发布笔记/提示词到广场"""
    obj = await service.publish(db, body.type, body.id, current_user.id)
    return success_response(
        data={"id": obj.id, "visibility": obj.visibility}, msg="发布成功"
    )


@router.put("/unpublish")
async def unpublish(
    body: PlazaActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """从广场取消发布"""
    obj = await service.unpublish(db, body.type, body.id, current_user.id)
    return success_response(
        data={"id": obj.id, "visibility": obj.visibility}, msg="已取消发布"
    )


@router.get("/items")
async def list_items(
    type: ContentType = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    tag: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """广场列表：浏览所有用户公开发布的内容"""
    rows, total = await service.list_items(db, type, page, page_size, search, tag)
    reactions = await _enrich_notes(db, type, [row[0] for row in rows], current_user.id)
    items = [
        _item_out(type, row[0], row[1], row[2], reactions.get(row[0].id)) for row in rows
    ]
    return success_response(
        data={"items": items, "total": total, "page": page, "page_size": page_size},
        msg="获取广场列表成功",
    )


@router.get("/items/{content_type}/{item_id}")
async def get_item(
    content_type: str,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """广场详情（只读全文）"""
    row = await service.get_public_item(db, content_type, item_id)
    obj, username, avatar = row[0], row[1], row[2]
    data = orm_to_dict(obj)
    data.update({
        "type": content_type,
        "author_id": obj.user_id,
        "author_username": username,
        "author_avatar": avatar,
        "forked_from": f"@{obj.source_username}" if obj.source_username else None,
    })
    if content_type == "note":
        reactions = await reaction_service.enrich(db, [obj.id], current_user.id)
        data.update(reactions.get(obj.id, {}))
    return success_response(
        data=PlazaDetailResponse.model_validate(data).model_dump(),
        msg="获取广场详情成功",
    )


@router.post("/fork")
async def fork(
    body: PlazaActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """一键复制广场内容为我的私有副本"""
    obj = await service.fork(db, body.type, body.id, current_user.id)
    return success_response(
        data={"id": obj.id, "title": obj.title}, msg="已复制到你的库", code=201
    )


@router.get("/mine")
async def list_mine(
    type: ContentType | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """我发布到广场的内容（管理用）"""
    pairs = await service.list_mine(db, current_user.id, type)
    note_objs = [obj for t, obj in pairs if t == "note"]
    reactions = await reaction_service.enrich(
        db, [o.id for o in note_objs], current_user.id
    ) if note_objs else {}
    items = [
        _item_out(t, obj, current_user.username, current_user.avatar, reactions.get(obj.id))
        for t, obj in pairs
    ]
    return success_response(data={"items": items, "total": len(items)}, msg="获取我的发布成功")


@router.put("/note/{note_id}/like")
async def toggle_like(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """切换广场笔记点赞状态"""
    data = await reaction_service.toggle(db, "like", note_id, current_user.id)
    return success_response(data=data, msg="操作成功")


@router.put("/note/{note_id}/favorite")
async def toggle_favorite(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """切换广场笔记收藏状态"""
    data = await reaction_service.toggle(db, "favorite", note_id, current_user.id)
    return success_response(data=data, msg="操作成功")


async def _my_reaction_items(db, kind, current_user, page, page_size):
    """我的点赞/收藏列表通用序列化"""
    rows, total = await reaction_service.list_mine_reactions(db, kind, current_user.id, page, page_size)
    objs = [row[0] for row in rows]
    reactions = await reaction_service.enrich(db, [o.id for o in objs], current_user.id)
    items = [
        _item_out("note", row[0], row[1], row[2], reactions.get(row[0].id)) for row in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/favorites")
async def list_my_favorites(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """我收藏的广场笔记"""
    data = await _my_reaction_items(db, "favorite", current_user, page, page_size)
    return success_response(data=data, msg="获取我的收藏成功")


@router.get("/likes")
async def list_my_likes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """我点赞的广场笔记"""
    data = await _my_reaction_items(db, "like", current_user, page, page_size)
    return success_response(data=data, msg="获取我的点赞成功")
