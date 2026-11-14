from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.constants import SIGNUP_BONUS_TOKENS
from app.core.security import hash_password, verify_password
from app.errors import AppError
from app.models import AccountKind, EntryType, User
from app.schemas.auth import SignupRequest
from app.services import ledger


def signup(db: Session, req: SignupRequest) -> User:
    """회원 생성 + 지갑 계정 생성 + 가입 보너스 지급을 한 트랜잭션에서 해요. (커밋은 호출한 쪽)"""
    if db.scalar(select(User.id).where(User.email == req.email)) is not None:
        raise AppError("EMAIL_TAKEN", "이미 가입된 이메일이에요", 409)

    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        nickname=req.nickname,
        school=req.school,
        major=req.major,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as e:  # 같은 이메일로 동시에 가입한 경우
        db.rollback()
        raise AppError("EMAIL_TAKEN", "이미 가입된 이메일이에요", 409) from e

    available, _ = ledger.create_user_accounts(db, user.id)
    system = ledger.get_system_user(db)
    issuance = ledger.get_account(db, system.id, AccountKind.SYSTEM_ISSUANCE)
    ledger.transfer(
        db,
        from_account_id=issuance.id,
        to_account_id=available.id,
        amount=SIGNUP_BONUS_TOKENS,
        entry_type=EntryType.SIGNUP_BONUS,
        idempotency_key=f"signup:{user.id}",
        memo="가입 축하 토큰",
    )
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None or user.is_system or not verify_password(password, user.password_hash):
        raise AppError("INVALID_CREDENTIALS", "이메일 또는 비밀번호가 맞지 않아요", 401)
    return user
