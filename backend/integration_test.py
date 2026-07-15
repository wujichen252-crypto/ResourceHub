"""Full integration test for ResourceHub backend API."""
import httpx

BASE = "http://localhost:8000/api"


def test():
    c = httpx.Client(base_url=BASE)

    # 0. Register (ignore if already exists)
    r = c.post("/auth/register", json={
        "username": "testuser", "password": "test123456", "email": "test@test.com"
    })
    if r.status_code == 201:
        print(f"[0] Register: {r.status_code}")
    elif r.status_code == 409:
        print(f"[0] User already exists (ok)")

    # 1. Login
    r = c.post("/auth/login", json={"username": "testuser", "password": "test123456"})
    print(f"[1] Login: {r.status_code}")
    assert r.status_code == 200
    t = r.json()["data"]["access_token"]
    h = {"Authorization": f"Bearer {t}"}
    print(f"    Token OK")

    # 2. Get user info
    r = c.get("/auth/me", headers=h)
    print(f"[2] Me: {r.status_code}, user={r.json()['data']['username']}")
    assert r.json()["data"]["username"] == "testuser"

    # 3. Create note category
    r = c.post("/categories", headers=h, json={"name": "技术", "type": "note"})
    nc = r.json()["data"]["id"]
    print(f"[3] Note category: {r.status_code}, id={nc}")
    assert r.status_code == 201

    # 4. Create sub-category
    r = c.post("/categories", headers=h, json={"name": "前端", "type": "note", "parent_id": nc})
    print(f"    Sub-category: {r.status_code}, id={r.json()['data']['id']}")

    # 5. Create note
    r = c.post("/notes", headers=h, json={
        "title": "FastAPI 入门",
        "content": "# FastAPI\n\nFastAPI is modern.",
        "category_id": nc,
        "tags": ["python", "fastapi"]
    })
    nid = r.json()["data"]["id"]
    print(f"[5] Note: {r.status_code}, id={nid}, pinned={r.json()['data']['is_pinned']}")
    assert r.status_code == 201

    # 6. List notes
    r = c.get("/notes", headers=h)
    print(f"[6] Notes list: total={r.json()['total']}")
    assert r.json()["total"] >= 1

    # 7. Pin note
    r = c.put(f"/notes/{nid}/pin", headers=h)
    print(f"[7] Pin: {r.status_code}, pinned={r.json()['data']['is_pinned']}")
    assert r.json()["data"]["is_pinned"] == True

    # 8. Create prompt category
    r = c.post("/categories", headers=h, json={"name": "编程", "type": "prompt"})
    pc = r.json()["data"]["id"]
    print(f"[8] Prompt category: {r.status_code}, id={pc}")

    # 9. Create prompt
    r = c.post("/prompts", headers=h, json={
        "title": "代码审查",
        "description": "审查代码",
        "content": "审查 {{lang}} 代码:\n```{{lang}}\n{{code}}\n```",
        "category_id": pc,
        "variables": ["lang", "code"]
    })
    pid = r.json()["data"]["id"]
    print(f"[9] Prompt: {r.status_code}, id={pid}")
    assert r.status_code == 201

    # 10. Render prompt
    r = c.post(f"/prompts/{pid}/render", headers=h, json={
        "variables": {"lang": "Python", "code": "print(1)"}
    })
    rendered = r.json()["data"]["rendered_content"]
    assert "Python" in rendered and "print(1)" in rendered
    print(f"[10] Render: {r.status_code}, OK")

    # 11. Favorite
    r = c.put(f"/prompts/{pid}/favorite", headers=h)
    print(f"[11] Favorite: {r.status_code}, fav={r.json()['data']['is_favorite']}")
    assert r.json()["data"]["is_favorite"] == True

    # 12. Record usage
    r = c.post(f"/prompts/{pid}/use", headers=h)
    print(f"[12] Use: {r.status_code}, count={r.json()['data']['usage_count']}")
    assert r.json()["data"]["usage_count"] == 1

    # 13. List favorite prompts
    r = c.get("/prompts?is_favorite=true", headers=h)
    print(f"[13] Fav list: {r.status_code}, total={r.json()['total']}")
    assert r.json()["total"] >= 1

    # 14. Category tree
    r = c.get("/categories?type=note", headers=h)
    tree = r.json()["data"]
    print(f"[14] Category tree: {len(tree)} roots")
    assert len(tree) >= 1

    # 15. Delete note
    r = c.delete(f"/notes/{nid}", headers=h)
    print(f"[15] Delete note: {r.status_code}")

    # 16. Verify deletion
    r = c.get(f"/notes/{nid}", headers=h)
    print(f"[16] Get deleted note: {r.status_code}")
    assert r.status_code == 404

    print()
    print("=" * 50)
    print("  ALL 16 TESTS PASSED!")
    print("=" * 50)


if __name__ == "__main__":
    test()
