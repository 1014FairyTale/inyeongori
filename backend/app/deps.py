from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.constants import REVIEW_DEADLINE_DAYS
from app.core.security import decode_access_token, token_predates_account
from app.db import get_db
from app.errors import AppError
from app.models import User
from app.services import review_policy

_bearer = HTTPBearer(auto_error=False)

DB = Annotated[Session, Depends(get_db)]


def get_logged_in_user(
    db: DB,
    cred: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    """로그인만 확인해요. 이용이 막힌 사람도 통과 (내 정보, 밀린 후기 쓰기 등에만 사용)."""
    if cred is None:
        raise AppError("UNAUTHORIZED", "로그인이 필요해요", 401)
    claims = decode_access_token(cred.credentials)
    user = db.get(User, claims.user_id) if claims is not None else None
    # 계정보다 먼저 발급된 토큰은 다른 사람(초기화 전 같은 번호) 것이라 거부해요
    if user is None or user.is_system or token_predates_account(claims, user.created_at):  # type: ignore[arg-type]
        raise AppError("UNAUTHORIZED", "로그인이 만료됐어요. 다시 로그인해 주세요", 401)
    return user


def get_current_user(db: DB, user: Annotated[User, Depends(get_logged_in_user)]) -> User:
    """로그인 + 이용 제한 확인. 완료 후 7일이 지나도록 후기를 안 쓴 거래가 있으면 막아요."""
    if review_policy.is_blocked(db, user):
        overdue = [d.exchange_id for d in review_policy.due_reviews(db, user) if d.overdue]
        raise AppError(
            "SERVICE_BLOCKED",
            f"완료 후 {REVIEW_DEADLINE_DAYS}일이 지난 거래의 후기를 남겨야 인연고리를 다시 이용할 수 있어요",
            403,
            {"overdue_exchange_ids": overdue},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
# 이용이 막혀도 쓸 수 있는 곳: 내 정보, 거래 상세 보기, 후기 쓰기·다시 분석·보기
LoggedInUser = Annotated[User, Depends(get_logged_in_user)]
