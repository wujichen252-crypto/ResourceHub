"""提示词模块回归测试 — 锁定版本/预设/渲染/统计契约"""

PROMPT_LIST_FIELDS = {"id", "title", "description", "category_id", "category_name",
                      "variables", "tags", "is_favorite", "usage_count",
                      "created_at", "updated_at"}
PROMPT_DETAIL_FIELDS = PROMPT_LIST_FIELDS | {"content"}
VERSION_FIELDS = {"id", "prompt_id", "version_number", "title", "description",
                  "content", "variables", "tags", "message", "labels",
                  "branch_name", "created_at"}


def _create_prompt(client, auth, content="审查 {{lang}} 代码", **kw):
    payload = {"title": "代码审查", "description": "审查用", "content": content,
               "category_id": None, "variables": ["lang"], "tags": ["dev"]}
    payload.update(kw)
    resp = client.post("/api/prompts", json=payload, headers=auth)
    assert resp.status_code == 201
    return resp.json()["data"]


def test_create_prompt_contract(client, auth):
    data = _create_prompt(client, auth)
    assert set(data) == PROMPT_DETAIL_FIELDS
    assert data["variables"] == ["lang"]
    assert data["tags"] == ["dev"]
    assert data["usage_count"] == 0


def test_list_contract_no_content(client, auth):
    _create_prompt(client, auth)
    resp = client.get("/api/prompts", headers=auth)
    item = resp.json()["data"]["items"][0]
    assert set(item) == PROMPT_LIST_FIELDS


def test_render_variables(client, auth):
    created = _create_prompt(client, auth)
    resp = client.post(
        f"/api/prompts/{created['id']}/render",
        json={"variables": {"lang": "Python"}},
        headers=auth,
    )
    data = resp.json()["data"]
    assert data["rendered_content"] == "审查 Python 代码"
    assert data["original_content"] == "审查 {{lang}} 代码"


def test_render_keeps_unknown_variable(client, auth):
    created = _create_prompt(client, auth)
    resp = client.post(
        f"/api/prompts/{created['id']}/render",
        json={"variables": {}},
        headers=auth,
    )
    assert "{{lang}}" in resp.json()["data"]["rendered_content"]


def test_version_snapshot_and_restore(client, auth):
    created = _create_prompt(client, auth, content="V1内容")
    pid = created["id"]

    client.put(f"/api/prompts/{pid}", json={"content": "V2内容"}, headers=auth)
    versions = client.get(f"/api/prompts/{pid}/versions", headers=auth).json()["data"]
    assert len(versions) == 2  # 初始快照 + 更新前快照
    assert versions[0]["version_number"] == 2
    assert {v["content"] for v in versions} == {"V1内容"}
    # 更新前快照保存的是旧内容，当前 prompt 已是新内容
    assert client.get(f"/api/prompts/{pid}", headers=auth).json()["data"]["content"] == "V2内容"

    # 恢复版本 v1 → 当前内容回滚，且先为恢复动作补拍快照
    v1 = versions[1]
    client.post(f"/api/prompts/{pid}/versions/{v1['id']}/restore", headers=auth)
    after = client.get(f"/api/prompts/{pid}", headers=auth).json()["data"]
    assert after["content"] == "V1内容"
    assert len(client.get(f"/api/prompts/{pid}/versions", headers=auth).json()["data"]) == 3


def test_version_fields_contract(client, auth):
    created = _create_prompt(client, auth)
    versions = client.get(f"/api/prompts/{created['id']}/versions", headers=auth).json()["data"]
    assert set(versions[0]) == VERSION_FIELDS
    assert versions[0]["labels"] == []
    assert versions[0]["branch_name"] == "main"


def test_diff_versions(client, auth):
    created = _create_prompt(client, auth, content="AAA")
    pid = created["id"]
    # 快照记录"变更前"状态：v1=AAA（初始），v2=AAA（第一次更新前），v3=AAB（第二次更新前）
    client.put(f"/api/prompts/{pid}", json={"content": "AAB"}, headers=auth)
    client.put(f"/api/prompts/{pid}", json={"content": "AAC"}, headers=auth)
    versions = client.get(f"/api/prompts/{pid}/versions", headers=auth).json()["data"]
    v3, v1 = versions[0], versions[-1]
    assert v3["content"] == "AAB" and v1["content"] == "AAA"
    resp = client.get(
        f"/api/prompts/{pid}/versions/{v1['id']}/diff",
        params={"target_version_id": v3["id"]},
        headers=auth,
    )
    data = resp.json()["data"]
    assert {"v1", "v2", "diffs"} <= set(data)
    assert all(seg["type"] in {"equal", "insert", "delete"} for seg in data["diffs"])
    assert any(seg["type"] == "delete" for seg in data["diffs"])
    assert any(seg["type"] == "insert" for seg in data["diffs"])


def test_labels_update(client, auth):
    created = _create_prompt(client, auth)
    versions = client.get(f"/api/prompts/{created['id']}/versions", headers=auth).json()["data"]
    resp = client.put(
        f"/api/prompts/{created['id']}/versions/{versions[0]['id']}/labels",
        json={"labels": ["production"]},
        headers=auth,
    )
    assert resp.json()["data"]["labels"] == ["production"]


def test_favorite_and_usage_and_analytics(client, auth):
    created = _create_prompt(client, auth)
    pid = created["id"]

    fav = client.put(f"/api/prompts/{pid}/favorite", headers=auth)
    assert fav.json()["data"] == {"id": pid, "is_favorite": True}

    client.post(f"/api/prompts/{pid}/use", headers=auth)
    used = client.post(f"/api/prompts/{pid}/use", headers=auth)
    assert used.json()["data"]["usage_count"] == 2

    analytics = client.get("/api/prompts/analytics/usage", headers=auth).json()["data"]
    assert set(analytics) == {"total_uses", "most_used", "daily_usage"}
    assert analytics["total_uses"] == 2
    assert analytics["most_used"][0]["count"] == 2


def test_presets_flow(client, auth):
    created = _create_prompt(client, auth)
    pid = created["id"]
    made = client.post(
        f"/api/prompts/{pid}/presets",
        json={"name": "Python预设", "values": {"lang": "Python"}},
        headers=auth,
    )
    assert made.status_code == 201
    preset_id = made.json()["data"]["id"]
    listed = client.get(f"/api/prompts/{pid}/presets", headers=auth).json()["data"]
    assert listed[0]["values"] == {"lang": "Python"}
    client.delete(f"/api/prompts/presets/{preset_id}", headers=auth)
    assert client.get(f"/api/prompts/{pid}/presets", headers=auth).json()["data"] == []


def test_delete_prompt_404(client, auth):
    created = _create_prompt(client, auth)
    client.delete(f"/api/prompts/{created['id']}", headers=auth)
    resp = client.get(f"/api/prompts/{created['id']}", headers=auth)
    assert resp.status_code == 404
    assert resp.json()["msg"] == "提示词不存在"
