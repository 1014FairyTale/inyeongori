from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db import get_db
from app.errors import AppError
from app.models import User

_bearer = HTTPBearer(auto_error=False)

DB = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DB,
    cred: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if cred is None:
        raise AppError("UNAUTHORIZED", "로그인이 필요해요", 401)
    user_id = decode_access_token(cred.credentials)
    user = db.get(User, user_id) if user_id is not None else None
    if user is None or user.is_system:
        raise AppError("UNAUTHORIZED", "로그인이 만료됐어요. 다시 로그인해 주세요", 401)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
