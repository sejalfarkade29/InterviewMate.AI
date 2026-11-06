from tests.conftest import register


def attempt_body(client_id="attempt-1"):
    return {"id": client_id, "module": "aptitude", "title": "Aptitude test", "score": 80, "maxScore": 100, "summary": "Question completed", "details": ["Good ratio reasoning"], "questionId": "apt-1", "level": 1}


def test_attempts_require_auth(client):
    assert client.get("/api/attempts").status_code == 401
    assert client.post("/api/attempts", json=attempt_body()).status_code == 401


def test_attempts_upsert_and_list(client):
    register(client)
    assert client.post("/api/attempts", json=attempt_body()).status_code == 201
    updated = attempt_body(); updated["score"] = 95
    assert client.post("/api/attempts", json=updated).json()["score"] == 95
    rows = client.get("/api/attempts").json()
    assert len(rows) == 1 and rows[0]["questionId"] == "apt-1"


def test_attempts_are_user_scoped(client):
    register(client, email="one@example.com")
    client.post("/api/attempts", json=attempt_body("one"))
    client.cookies.clear()
    register(client, email="two@example.com")
    assert client.get("/api/attempts").json() == []
