"""资源广场笔记互动服务：点赞/收藏 toggle、列表富化、我的点赞/收藏列表

设计要点：
- 不存冗余计数，计数一律查询时 COUNT(*) 派生，避免漂移
- 列表富化用后置批量查询（IN + GROUP BY），每页至多 4 条 SQL，杜绝 N+1
- 唯一索引 (note_id, user_id) 兜底并发，INSERT 冲突视为已存在
"""
from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode, get_error_message
from app.models.note import Note
from app.models.note_reaction import NoteFavorite, NoteLike
from app.models.user import User

# 互动类型 → (关系表模型, 状态字段名, 计数字段名)
_REACTION = {
    "like": (NoteLike, "liked", "like_count"),
    "favorite": (NoteFavorite, "favorited", "favorite_count"),
}


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": ErrorCode.PLAZA_ITEM_NOT_FOUND,
            "message": get_error_message(ErrorCode.PLAZA_ITEM_NOT_FOUND),
        },
    )


def _own_note() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "code": ErrorCode.CANNOT_REACT_OWN_NOTE,
            "message": get_error_message(ErrorCode.CANNOT_REACT_OWN_NOTE),
        },
    )


class PlazaReactionService:
    async def toggle(self, db: AsyncSession, kind: str, note_id: int, user_id: int) -> dict:
        """切换点赞/收藏状态，返回 {状态字段: bool, 计数字段: int}"""
        model, state_field, count_field = _REACTION[kind]

        note = (
            await db.execute(select(Note).where(Note.id == note_id))
        ).scalar_one_or_none()
        if note is None or note.visibility != "public":
            raise _not_found()
        if note.user_id == user_id:
            raise _own_note()

        existing = (
            await db.execute(
                select(model).where(model.note_id == note_id, model.user_id == user_id)
            )
        ).scalar_one_or_none()

        if existing is not None:
            await db.execute(delete(model).where(model.id == existing.id))
            await db.commit()
            active = False
        else:
            try:
                db.add(model(note_id=note_id, user_id=user_id))
                await db.commit()
                active = True
            except IntegrityError:
                # 并发重复插入：唯一索引兜底，视为已点赞
                await db.rollback()
                active = True

        count = (
            await db.execute(
                select(func.count()).where(model.note_id == note_id)
            )
        ).scalar() or 0
        return {state_field: active, count_field: count}

    async def enrich(self, db: AsyncSession, note_ids: list[int], user_id: int) -> dict[int, dict]:
        """批量返回每篇笔记的 {like_count, favorite_count, liked, favorited}

        每类互动各 2 条 SQL（计数 + 当前用户是否已操作），与页大小无关。
        """
        if not note_ids:
            return {}

        result: dict[int, dict] = {
            nid: {
                "like_count": 0,
                "favorite_count": 0,
                "liked": False,
                "favorited": False,
            }
            for nid in note_ids
        }

        for model, count_key, state_key in (
            (NoteLike, "like_count", "liked"),
            (NoteFavorite, "favorite_count", "favorited"),
        ):
            # 计数
            counts = (
                await db.execute(
                    select(model.note_id, func.count())
                    .where(model.note_id.in_(note_ids))
                    .group_by(model.note_id)
                )
            ).all()
            for nid, cnt in counts:
                result[nid][count_key] = cnt
            # 当前用户已操作集合
            mine = (
                await db.execute(
                    select(model.note_id).where(
                        model.note_id.in_(note_ids), model.user_id == user_id
                    )
                )
            ).scalars().all()
            for nid in mine:
                result[nid][state_key] = True

        return result

    async def list_mine_reactions(
        self, db: AsyncSession, kind: str, user_id: int, page: int, page_size: int
    ):
        """我的点赞/收藏列表：仅仍 public 的笔记，按操作时间倒序，join 作者信息"""
        model = _REACTION[kind][0]

        query = (
            select(Note, User.username, User.avatar, model.created_at)
            .join(model, model.note_id == Note.id)
            .join(User, User.id == Note.user_id)
            .where(model.user_id == user_id, Note.visibility == "public")
        )

        total = (
            await db.execute(select(func.count()).select_from(query.subquery()))
        ).scalar() or 0

        query = query.order_by(model.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(query)).all()
        return rows, total


reaction_service = PlazaReactionService()
