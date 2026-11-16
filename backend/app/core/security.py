from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.config import get_settings

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def create_access_token(user_id: int) -> str:
    s = get_settings()
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=s.jwt_expire_minutes)}
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


@dataclass(frozen=True)
class TokenClaims:
    user_id: int
    issued_at: datetime


# 토큰 발급 시각(iat)은 초 단위로 잘리고, 계정 생성 시각은 DB 시계로 기록돼요. 그 오차만큼 여유를 둬요.
TOKEN_ISSUED_BEFORE_ACCOUNT_TOLERANCE = timedelta(seconds=5)


def decode_access_token(token: str) -> TokenClaims | None:
    s = get_settings()
    try:
        payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm], options={"require": ["sub", "iat", "exp"]})
        return TokenClaims(int(payload["sub"]), datetime.fromtimestamp(int(payload["iat"]), UTC))
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        return None


def token_predates_account(claims: TokenClaims, account_created_at: datetime) -> bool:
    """계정이 만들어지기 전에 발급된 토큰인지.
    DB를 초기화하면 사용자 번호가 1번부터 다시 매겨져서, 예전 토큰이 같은 번호의 다른 사람을 가리킬 수 있어요."""
    return claims.issued_at < account_created_at - TOKEN_ISSUED_BEFORE_ACCOUNT_TOLERANCE
