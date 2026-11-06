from tests.conftest import register


def test_register_sets_cookie_and_returns_user(client):
    r = register(client)
    assert r.status_code == 201
    assert r.json()["email"] == "sejal@example.com"
    assert "access_token" in r.cookies
    assert "password" not in r.text


def test_register_duplicate_email_rejected(client):
    register(client)
    assert register(client, email="SEJAL@example.com").status_code == 409


def test_register_weak_password_rejected(client):
    assert register(client, password="short1").status_code == 422
    assert register(client, password="onlyletters").status_code == 422


def test_register_invalid_email_rejected(client):
    assert register(client, email="not-an-email").status_code == 422


def test_login_success_and_me(client):
    register(client)
    client.cookies.clear()
    r = client.post("/api/auth/login", json={"email": "sejal@example.com", "password": "Passw0rdOK"})
    assert r.status_code == 200
    me = client.get("/api/auth/me")
    assert me.status_code == 200 and me.json()["full_name"] == "Sejal F"


def test_login_wrong_password_same_message_as_unknown_email(client):
    register(client)
    client.cookies.clear()
    a = client.post("/api/auth/login", json={"email": "sejal@example.com", "password": "wrongpass1"})
    b = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "wrongpass1"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_me_requires_authentication(client):
    assert client.get("/api/auth/me").status_code == 401


def test_logout_clears_session(client):
    register(client)
    assert client.post("/api/auth/logout").status_code == 204
    client.cookies.clear()
    assert client.get("/api/auth/me").status_code == 401


def test_tampered_token_rejected(client):
    client.cookies.set("access_token", "not.a.real.token")
    assert client.get("/api/auth/me").status_code == 401


def test_login_rate_limited(client):
    register(client)
    client.cookies.clear()
    codes = [
        client.post("/api/auth/login", json={"email": "sejal@example.com", "password": "bad-pass-1"}).status_code
        for _ in range(12)
    ]
    assert 429 in codes
