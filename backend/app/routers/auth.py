from datetime import UTC, datetime

from fastapi import APIRouter, status

from app.core.security import create_access_token
from app.deps import DB, LoggedInUser
from app.models import User
from app.schemas.auth import (
    DueReviewOut,
    GettingStarted,
    LoginRequest,
    MeOut,
    ReviewStatus,
    SignupRequest,
    StepOut,
    TokenOut,
    UserOut,
    WalletBrief,
)
from app.services import auth as auth_service
from app.services import getting_started, ledger, review_policy

router = APIRouter(prefix="/auth", tags=["auth"])


def _me(db: DB, user: User) -> MeOut:
    w = ledger.wallet_summary(db, user.id)
    due = review_policy.due_reviews(db, user)
    return MeOut(
        user=UserOut.model_validate(user),
        wallet=WalletBrief(available=w.available, escrow=w.escrow),
        review_status=ReviewStatus(
            blocked=any(d.overdue for d in due),
            due=[DueReviewOut(**d.__dict__) for d in due],
        ),
        getting_started=GettingStarted(
            tutorial_seen=user.tutorial_seen_at is not None,
            steps=[StepOut(key=s.key, done=s.done) for s in getting_started.steps(db, user)],
        ),
    )


@router.post("/signup", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def signup(req: SignupRequest, db: DB) -> TokenOut:
    user = auth_service.signup(db, req)
    db.commit()
    return TokenOut(access_token=create_access_token(user.id), me=_me(db, user))


@router.post("/login", response_model=TokenOut)
def login(req: LoginRequest, db: DB) -> TokenOut:
    user = auth_service.authenticate(db, req.email, req.password)
    return TokenOut(access_token=create_access_token(user.id), me=_me(db, user))


@router.get("/me", response_model=MeOut)
def me(user: LoggedInUser, db: DB) -> MeOut:
    return _me(db, user)


@router.post("/me/tutorial", response_model=MeOut)
def tutorial_seen(user: LoggedInUser, db: DB) -> MeOut:
    """이용 가이드를 끝까지 보거나 건너뛰면 기록해요 (다시 자동으로 띄우지 않게)."""
    if user.tutorial_seen_at is None:
        user.tutorial_seen_at = datetime.now(UTC)
        db.commit()
    return _me(db, user)
