from fastapi import APIRouter, status

from app.deps import DB, LoggedInUser
from app.errors import AppError
from app.models import Exchange, Review
from app.schemas.review import AnalysisOut, PublicReview, ReviewCreate, ReviewOut, ReviewOutBase
from app.services import exchange_flow, reviews

router = APIRouter(tags=["reviews"])


def _out(db: DB, review: Review, *, failed: bool = False) -> ReviewOut:
    a = reviews.get_analysis(db, review.id)
    return ReviewOut(
        review=ReviewOutBase.model_validate(review),
        analysis=AnalysisOut.model_validate(a) if a else None,
        analysis_failed=failed and a is None,
    )


@router.post("/exchanges/{exchange_id}/review", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def create_review(exchange_id: int, req: ReviewCreate, user: LoggedInUser, db: DB) -> ReviewOut:
    """후기 저장 → AI 분석 → 조건을 넘으면 제공자에게 보너스. AI가 실패해도 후기는 저장돼요."""
    review = reviews.create_review(db, user, exchange_id, req.rating, req.good_text, req.bad_text)
    analysis = reviews.analyze(db, review)
    db.commit()
    return _out(db, review, failed=analysis is None)


@router.post("/exchanges/{exchange_id}/review/analyze", response_model=ReviewOut)
def retry_analysis(exchange_id: int, user: LoggedInUser, db: DB) -> ReviewOut:
    review = reviews.get_review(db, exchange_id)
    if review is None or review.reviewer_id != user.id:
        raise AppError("NOT_FOUND", "후기를 찾을 수 없어요", 404)
    analysis = reviews.analyze(db, review)
    db.commit()
    return _out(db, review, failed=analysis is None)


@router.get("/exchanges/{exchange_id}/review", response_model=ReviewOut | None)
def get_review(exchange_id: int, user: LoggedInUser, db: DB) -> ReviewOut | None:
    ex = db.get(Exchange, exchange_id)
    if ex is None:
        raise AppError("NOT_FOUND", "거래를 찾을 수 없어요", 404)
    exchange_flow.role_of(ex, user)  # 당사자만
    review = reviews.get_review(db, exchange_id)
    return _out(db, review) if review else None


@router.get("/users/{user_id}/reviews", response_model=list[PublicReview])
def user_reviews(user_id: int, db: DB) -> list[PublicReview]:
    return [
        PublicReview(
            id=r.id,
            rating=r.rating,
            good_text=r.good_text,
            bad_text=r.bad_text,
            reviewer_nickname=nick,
            listing_title=title,
            contribution_score=a.contribution_score if a else None,
            bonus=a.final_bonus if a else 0,
            created_at=r.created_at,
        )
        for r, a, nick, title in reviews.reviews_of(db, user_id)
    ]
