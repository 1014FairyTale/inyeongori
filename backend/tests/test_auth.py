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


def test_token_issued_before_account_is_rejected(client: TestClient, db) -> None:  # noqa: ANN001
    """DB를 초기화하면 사용자 번호가 다시 매겨져요. 예전 토큰이 같은 번호의 새 계정으로 로그인되면 안 돼요."""
    from datetime import timedelta

    from sqlalchemy import update

    from app.models import User

    body = signup(client, "old@example.com")
    old_token = body["access_token"]
    user_id = body["me"]["user"]["id"]
    # 초기화 뒤 같은 번호로 새 계정이 1분 뒤에 만들어진 상황
    db.execute(update(User).where(User.id == user_id).values(created_at=User.created_at + timedelta(minutes=1)))
    db.commit()

    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"


def test_token_without_issued_at_is_rejected(client: TestClient) -> None:
    import jwt

    from app.config import get_settings

    body = signup(client, "noiat@example.com")
    s = get_settings()
    forged = jwt.encode({"sub": str(body["me"]["user"]["id"]), "exp": 4102444800}, s.jwt_secret, algorithm=s.jwt_algorithm)
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401
