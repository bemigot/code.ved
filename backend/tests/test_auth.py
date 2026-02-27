"""Tests for auth endpoints and role enforcement."""


def test_login_ed1_returns_roles(client):
    r = client.post("/api/auth/login", json={"username": "ed1", "password": "1editor"})
    assert r.status_code == 200
    data = r.json()
    assert data["username"] == "ed1"
    assert "editor" in data["roles"]
    assert "viewer" in data["roles"]


def test_login_mo1_returns_viewer_only(client):
    r = client.post("/api/auth/login", json={"username": "mo1", "password": "2viewer"})
    assert r.status_code == 200
    data = r.json()
    assert data["username"] == "mo1"
    assert data["roles"] == ["viewer"]


def test_login_bad_password(client):
    r = client.post("/api/auth/login", json={"username": "ed1", "password": "wrong"})
    assert r.status_code == 401


def test_login_unknown_user(client):
    r = client.post("/api/auth/login", json={"username": "nobody", "password": "x"})
    assert r.status_code == 401


def test_me_returns_user_info(ed1):
    r = ed1.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["username"] == "ed1"


def test_me_unauthenticated(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_logout_clears_session(ed1):
    r = ed1.post("/api/auth/logout")
    assert r.status_code == 200
    r2 = ed1.get("/api/auth/me")
    assert r2.status_code == 401


def test_viewer_can_list_scripts(mo1):
    r = mo1.get("/api/scripts")
    assert r.status_code == 200


def test_viewer_cannot_create_script(mo1):
    r = mo1.post("/api/scripts", json={"content": ""})
    assert r.status_code == 403


def test_unauthenticated_cannot_list_scripts(client):
    r = client.get("/api/scripts")
    assert r.status_code == 401


def test_unauthenticated_cannot_create_script(client):
    r = client.post("/api/scripts", json={"content": ""})
    assert r.status_code == 401
