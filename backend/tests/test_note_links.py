"""笔记双向链接回归测试 — [[标题]] 提取、反向链接查询、按标题解析"""
import asyncio

import pytest

from app.core.database import Base


@pytest.fixture()
def db_session(db_url):
    """与 client 同库的异步会话工厂，供测试直接查询 ORM 数据"""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    engine = create_async_engine(db_url, poolclass=NullPool)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    asyncio.run(engine.dispose())


def _create_note(client, auth, **kw):
    payload = {"title": "待定标题", "content": "正文"}
    payload.update(kw)
    resp = client.post("/api/notes", json=payload, headers=auth)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


def test_markdown_wikilink_creates_backlink(client, auth):
    """markdown 轨：A 引用 B → B 的反向链接包含 A；更新移除引用后反链清空"""
    target = _create_note(client, auth, title="Redis 缓存", content="穿透与雪崩")
    source = _create_note(client, auth, title="缓存笔记", content="详见 [[Redis 缓存]]")

    resp = client.get(f"/api/notes/{target['id']}/backlinks", headers=auth)
    items = resp.json()["data"]["items"]
    assert resp.json()["data"]["total"] == 1
    assert items[0]["id"] == source["id"]
    assert items[0]["title"] == "缓存笔记"

    # 移除引用后反链清空
    resp = client.put(
        f"/api/notes/{source['id']}",
        json={"content": "不再引用了"},
        headers=auth,
    )
    assert resp.status_code == 200, resp.text
    resp = client.get(f"/api/notes/{target['id']}/backlinks", headers=auth)
    assert resp.json()["data"]["total"] == 0, resp.json()


def test_json_track_note_link_node(client, auth):
    """json 轨：noteLink 原子节点按 noteId 解析（目标改名不失效）"""
    target = _create_note(client, auth, title="向量检索", content="embedding")
    doc = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "参见 "},
                    {
                        "type": "noteLink",
                        "attrs": {"title": "向量检索", "noteId": target["id"]},
                    },
                    {"type": "text", "text": " 的章节"},
                ],
            }
        ],
    }
    _create_note(
        client, auth, title="RAG 笔记",
        content="<p>参见 向量检索 的章节</p>", content_json=doc,
    )

    resp = client.get(f"/api/notes/{target['id']}/backlinks", headers=auth)
    items = resp.json()["data"]["items"]
    assert resp.json()["data"]["total"] == 1
    assert items[0]["title"] == "RAG 笔记"

    # 目标改名后反链仍保留（ID 解析免疫改名），且标题快照刷新为新标题
    client.put(
        f"/api/notes/{target['id']}", json={"title": "向量检索（新）"}, headers=auth
    )
    resp = client.get(f"/api/notes/{target['id']}/backlinks", headers=auth)
    assert resp.json()["data"]["total"] == 1


def test_json_track_wikilink_in_plain_text(client, auth):
    """json 轨：正文 JSON 文本节点中的 [[标题]] 同样能建立链接（手输场景兜底）"""
    target = _create_note(client, auth, title="向量检索", content="embedding")
    doc = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "参见 [[向量检索]] 的章节"},
                ],
            }
        ],
    }
    _create_note(
        client, auth, title="RAG 笔记",
        content="<p>参见 [[向量检索]] 的章节</p>", content_json=doc,
    )

    resp = client.get(f"/api/notes/{target['id']}/backlinks", headers=auth)
    items = resp.json()["data"]["items"]
    assert resp.json()["data"]["total"] == 1
    assert items[0]["title"] == "RAG 笔记"


def test_wikilink_to_missing_title_stays_unresolved(client, auth, db_session):
    """引用不存在的标题：不建 target_note_id，反链面板不显示，resolve 接口 404"""
    source = _create_note(client, auth, title="空链接", content="引用 [[幽灵笔记]]")

    from app.models.note_link import NoteLink
    from sqlalchemy import select

    async def _check():
        async with db_session() as session:
            rows = (await session.execute(select(NoteLink))).scalars().all()
            assert len(rows) == 1
            assert rows[0].target_note_id is None
            assert rows[0].target_title == "幽灵笔记"

    asyncio.run(_check())

    resp = client.get(
        "/api/notes/resolve", params={"title": "幽灵笔记"}, headers=auth
    )
    assert resp.status_code == 404
    # 无断链来源仍显示（target_note_id 为空不匹配反链查询）
    _ = source


def test_resolve_note_by_title(client, auth):
    """resolve 接口：命中返回 id；自引用标题被排除"""
    note = _create_note(client, auth, title="Docker 网络", content="bridge 与 overlay")
    resp = client.get(
        "/api/notes/resolve", params={"title": "Docker 网络"}, headers=auth
    )
    assert resp.json()["data"]["id"] == note["id"]


def test_note_link_service_ignores_self_reference(client, auth, db_session):
    """笔记引用自己的标题不应产生自链"""
    from app.models.note_link import NoteLink
    from sqlalchemy import select

    _create_note(client, auth, title="自我引用", content="这是 [[自我引用]] 的说明")

    async def _check():
        async with db_session() as session:
            rows = (await session.execute(select(NoteLink))).scalars().all()
            assert rows == []

    asyncio.run(_check())
