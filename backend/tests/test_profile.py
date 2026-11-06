from tests.conftest import register


def test_profile_requires_auth(client):
    assert client.get("/api/profile").status_code == 401
    assert client.put("/api/profile", json={"full_name": "X"}).status_code == 401


def test_new_profile_is_empty(client):
    register(client)
    p = client.get("/api/profile").json()
    assert p["full_name"] == "Sejal F" and p["completeness"] == 0 and p["skills"] == []


def test_update_profile_persists_and_computes_completeness(client):
    register(client)
    body = {
        "full_name": "Sejal Farkade", "college": "ABC University", "degree": "B.Tech",
        "branch": "Computer Science", "graduation_year": 2027,
        "skills": ["Python", "python", " SQL "], "experience_level": "student",
        "preferred_roles": ["AI Engineer"],
    }
    r = client.put("/api/profile", json=body)
    assert r.status_code == 200
    data = client.get("/api/profile").json()
    assert data["skills"] == ["Python", "SQL"]  # de-duplicated and trimmed
    assert data["completeness"] == 78  # 7 of 9 tracked fields filled


def test_profile_validation(client):
    register(client)
    assert client.put("/api/profile", json={"full_name": "A", "graduation_year": 1900}).status_code == 422
    assert client.put("/api/profile", json={"full_name": "A", "experience_level": "wizard"}).status_code == 422
    assert client.put("/api/profile", json={"full_name": ""}).status_code == 422


def test_users_cannot_see_each_others_profiles(client):
    register(client, email="a@example.com", name="User A")
    client.put("/api/profile", json={"full_name": "User A", "college": "Private College A"})
    client.cookies.clear()
    register(client, email="b@example.com", name="User B")
    p = client.get("/api/profile").json()
    assert p["full_name"] == "User B" and p["college"] is None
