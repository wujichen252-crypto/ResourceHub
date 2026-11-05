"""
搜索适配层测试
- 未启用/服务不可用时安全降级（返回 None → 上游回落 LIKE）
- 启用时强制按 user_id 过滤，避免跨用户召回
"""
import asyncio

import httpx
import pytest

from app.core.config import settings
from app.services import search_service as search_module
from app.services.search_service import SearchService, strip_html


@pytest.fixture(autouse=True)
def _reset_state():
    """每个用例重置索引就绪标记与单例客户端"""
    search_module._index_ready = False
    yield
    search_module._index_ready = False
    search_module.search_service._client = None


def _service_with_transport(handler):
    """构造挂载 MockTransport 的适配层实例"""
    svc = SearchService()
    svc._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="http://meili.test",
    )
    return svc


def test_strip_html_removes_tags_and_entities():
    assert strip_html("<p>你好&nbsp;<b>世界</b></p>") == "你好 世界"
    assert strip_html(None) == ""
    assert strip_html("") == ""


def test_search_disabled_returns_none(monkeypatch):
    """未启用时直接短路，调用方回落 LIKE"""
    monkeypatch.setattr(settings, "MEILI_ENABLED", False)
    assert asyncio.run(search_module.search_service.search_note_ids(1, "笔记")) is None


def test_search_service_down_returns_none(monkeypatch):
    """服务不可达时返回 None，不抛出异常影响主流程"""
    monkeypatch.setattr(settings, "MEILI_ENABLED", True)
    monkeypatch.setattr(settings, "MEILI_URL", "http://meili.test")

    def _boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    svc = _service_with_transport(_boom)
    assert asyncio.run(svc.search_note_ids(1, "笔记")) is None


def test_search_hits_carry_user_id_filter(monkeypatch):
    """命中的查询必须带 user_id 过滤，且按返回顺序提取 ID"""
    monkeypatch.setattr(settings, "MEILI_ENABLED", True)
    monkeypatch.setattr(settings, "MEILI_URL", "http://meili.test")
    monkeypatch.setattr(settings, "MEILI_INDEX", "notes")
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/indexes":
            return httpx.Response(409, json={"message": "index already exists"})
        if request.method == "PATCH" and request.url.path.endswith("/settings"):
            return httpx.Response(202, json={"taskUid": 1})
        if request.url.path.endswith("/search"):
            captured["body"] = request.read().decode()
            return httpx.Response(200, json={"hits": [{"id": 7}, {"id": 2}]})
        return httpx.Response(200, json={})

    svc = _service_with_transport(handler)
    ids = asyncio.run(svc.search_note_ids(42, "笔记"))

    assert ids == [7, 2]
    assert "user_id = 42" in captured["body"]


def test_index_note_disabled_returns_false(monkeypatch):
    monkeypatch.setattr(settings, "MEILI_ENABLED", False)
    svc = SearchService()
    assert asyncio.run(svc.index_note(object())) is False  # 未启用时不触达任何属性


def test_build_document_parses_json_tags_and_strips_html():
    """索引文档：tags 从 JSON 字符串还原为数组，正文去标签"""
    from app.models.note import Note

    note = Note(
        id=1,
        user_id=9,
        title="FastAPI 入门",
        content="<h1>标题</h1><p>正文</p>",
        tags='["python", "fastapi"]',
        is_pinned=False,
    )
    doc = SearchService.build_document(note)
    assert doc["tags"] == ["python", "fastapi"]
    assert doc["content_text"] == "标题 正文"
    assert doc["user_id"] == 9
    assert doc["updated_at"] == 0  # 未落库时无时间戳，保持可索引


def test_batch_index_and_stats(monkeypatch):
    """批量回填：一次请求提交多条文档；stats 读取索引文档数"""
    from app.models.note import Note

    monkeypatch.setattr(settings, "MEILI_ENABLED", True)
    monkeypatch.setattr(settings, "MEILI_URL", "http://meili.test")
    monkeypatch.setattr(settings, "MEILI_INDEX", "notes")
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/indexes":
            return httpx.Response(409, json={"message": "index already exists"})
        if request.method == "PATCH" and request.url.path.endswith("/settings"):
            return httpx.Response(202, json={"taskUid": 1})
        if request.method == "POST" and request.url.path.endswith("/documents"):
            captured["docs"] = request.read().decode()
            return httpx.Response(202, json={"taskUid": 2})
        if request.url.path.endswith("/stats"):
            return httpx.Response(200, json={"numberOfDocuments": 42})
        return httpx.Response(200, json={})

    svc = _service_with_transport(handler)
    notes = [
        Note(id=1, user_id=1, title="A", content="<p>x</p>", tags="[]", is_pinned=False),
        Note(id=2, user_id=1, title="B", content="<p>y</p>", tags="[]", is_pinned=False),
    ]
    assert asyncio.run(svc.index_notes(notes)) is True
    assert '"id":1' in captured["docs"] and '"id":2' in captured["docs"]
    assert asyncio.run(svc.stats()) == 42


def test_search_falls_back_to_like_when_meili_disabled(client, auth):
    """Meili 关闭时，/api/notes 搜索仍按 LIKE 命中（零回归）"""
    client.post(
        "/api/notes",
        json={"title": "容错测试", "content": "独特关键词abcxyz", "tags": []},
        headers=auth,
    )
    resp = client.get("/api/notes", params={"search": "abcxyz"}, headers=auth)
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 1


def test_empty_meili_hits_fall_back_to_like(client, auth, monkeypatch):
    """索引尚未回填时 Meili 返回空列表，仍需命中存量笔记（回落 LIKE）"""
    client.post(
        "/api/notes",
        json={"title": "存量笔记", "content": "关键词oldnote", "tags": []},
        headers=auth,
    )

    async def empty_search(user_id: int, keyword: str, limit: int = 200):
        return []

    monkeypatch.setattr(
        search_module.search_service, "search_note_ids", empty_search
    )
    resp = client.get("/api/notes", params={"search": "oldnote"}, headers=auth)
    assert resp.json()["data"]["total"] == 1


def test_search_uses_meili_hit_ids(client, auth, monkeypatch):
    """Meili 可用时以命中 ID 过滤，且不跨用户返回"""
    note = client.post(
        "/api/notes",
        json={"title": "容错测试", "content": "正文", "tags": []},
        headers=auth,
    ).json()["data"]
    other = client.post(
        "/api/notes",
        json={"title": "他人笔记", "content": "正文", "tags": []},
        headers=auth,
    ).json()["data"]

    async def fake_search(user_id: int, keyword: str, limit: int = 200):
        return [note["id"]]

    monkeypatch.setattr(
        search_module.search_service, "search_note_ids", fake_search
    )
    resp = client.get("/api/notes", params={"search": "任意词"}, headers=auth)
    ids = [item["id"] for item in resp.json()["data"]["items"]]
    assert ids == [note["id"]]
    assert other["id"] not in ids
