from fastapi.testclient import TestClient

from tests.conftest import signup


def test_signup_gives_100_tokens(client: TestClient) -> None:
    body = signup(client)
    assert body["access_token"]
    assert body["me"]["wallet"] == {"available": 100, "escrow": 0}
    assert body["me"]["user"]["nickname"] == "새내기"


def test_signup_duplicate_email_is_rejected(client: TestClient) -> None:
    signup(client, "dup@example.com")
    r = client.post(
        "/api/v1/auth/signup",
        json={"email": "DUP@example.com", "password": "password123", "nickname": "또"},
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "EMAIL_TAKEN"


def test_login_and_me(client: TestClient) -> None:
    signup(client, "me@example.com")
    r = client.post("/api/v1/auth/login", json={"email": "me@example.com", "password": "password123"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["wallet"]["available"] == 100


def test_login_wrong_password(client: TestClient) -> None:
    signup(client, "x@example.com")
    r = client.post("/api/v1/auth/login", json={"email": "x@example.com", "password": "wrong-pass"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_system_account_cannot_login(client: TestClient) -> None:
    r = client.post("/api/v1/auth/login", json={"email": "system@inyeongori.local", "password": "!"})
    assert r.status_code in (401, 422)


def test_me_requires_token(client: TestClient) -> None:
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401
    assert r.json() == {"error": {"code": "UNAUTHORIZED", "message": "로그인이 필요해요", "details": {}}}


def test_validation_error_format(client: TestClient) -> None:
    r = client.post("/api/v1/auth/signup", json={"email": "bad", "password": "short", "nickname": ""})
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    fields = {f["field"] for f in err["details"]["fields"]}
    assert {"email", "password", "nickname"} <= fields
