"""후기 작성 → AI 분석 → 보너스 지급 (기능 8).

- 후기는 거래가 '완료'된 뒤 요청자만, 거래당 한 번 쓸 수 있어요.
- AI 분석이 실패해도 후기는 저장돼요. 나중에 '다시 분석'으로 이어서 할 수 있어요.
- 분석·보너스 지급은 한 트랜잭션에서 하고, 지급은 멱등 키(review_bonus:{exchange_id})로 한 번만 일어나요.
"""

import logging

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ai.providers.base import AIError
from ai.schemas import ReviewAnalysisAI
from ai.structured import generate
from app.config import get_settings
from app.errors import AppError
from app.models import Agreement, Exchange, ExchangeStatus, Listing, Review, ReviewAnalysis, User
from app.services import bonus, exchange_flow

log = logging.getLogger("reviews")


def get_review(db: Session, exchange_id: int) -> Review | None:
    return db.scalar(select(Review).where(Review.exchange_id == exchange_id))


def get_analysis(db: Session, review_id: int) -> ReviewAnalysis | None:
    return db.scalar(select(ReviewAnalysis).where(ReviewAnalysis.review_id == review_id))


def create_review(db: Session, user: User, exchange_id: int, rating: int, good: str, bad: str | None) -> Review:
    ex = exchange_flow.lock_exchange(db, exchange_id)
    role = exchange_flow.role_of(ex, user)
    if ex.status != ExchangeStatus.COMPLETED:
        raise AppError("INVALID_STATE", "거래가 완료된 뒤에 후기를 쓸 수 있어요", 409)
    if role != "requester":
        raise AppError("FORBIDDEN", "후기는 도움을 받은 요청자가 써요", 403)
    if get_review(db, ex.id) is not None:
        raise AppError("ALREADY_REVIEWED", "이미 후기를 남겼어요", 409)

    review = Review(
        exchange_id=ex.id,
        reviewer_id=ex.requester_id,
        reviewee_id=ex.provider_id,
        rating=rating,
        good_text=good.strip(),
        bad_text=(bad or "").strip() or None,
    )
    db.add(review)
    try:
        db.flush()
    except IntegrityError as e:
        raise AppError("ALREADY_REVIEWED", "이미 후기를 남겼어요", 409) from e
    return review


def _prompt(db: Session, ex: Exchange, review: Review) -> str:
    listing = db.get(Listing, ex.listing_id) if ex.listing_id else None
    ag = db.scalar(select(Agreement).where(Agreement.exchange_id == ex.id).order_by(Agreement.version.desc()).limit(1))
    terms = ag.terms if ag else {}
    label = {"request_text": "요청", "scope": "범위", "quantity": "분량", "revisions": "수정 횟수", "duration_minutes": "소요 시간(분)", "notes": "기타"}
    lines = [
        "## 재능 상품",
        f"- 제목: {listing.title if listing else '(삭제됨)'}",
        f"- 거래 가격: {ex.price_tokens}토큰",
        "",
        "## 거래 전에 합의한 조건",
        *[f"- {label.get(k, k)}: {v}" for k, v in terms.items() if v not in (None, "")],
        "",
        "## 후기",
        f"- 별점: {review.rating}/5",
        f"- 좋았던 점: {review.good_text}",
        f"- 아쉬운 점: {review.bad_text or '(없음)'}",
    ]
    return "\n".join(lines)


def analyze(db: Session, review: Review) -> ReviewAnalysis | None:
    """AI 분석 + 보너스 지급. AI가 실패하면 None (후기는 그대로 남아요)."""
    existing = get_analysis(db, review.id)
    if existing is not None:
        return existing
    ex = db.get(Exchange, review.exchange_id)
    assert ex is not None

    try:
        ai = generate("review_analysis", _prompt(db, ex, review), ReviewAnalysisAI)
    except AIError as e:
        log.warning("review analysis failed review=%s: %s", review.id, e)
        return None

    bonus.lock_provider_account(db, ex.provider_id)
    decision = bonus.decide(db, ex, review, ai.contribution_score)
    s = get_settings()
    analysis = ReviewAnalysis(
        review_id=review.id,
        reviewee_id=ex.provider_id,
        contribution_score=ai.contribution_score,
        summary=ai.summary,
        reasons=ai.reasons,
        flags=ai.flags,
        ai_provider="mock" if s.ai_mock else s.llm_model,
        eligible=decision.eligible,
        base_bonus=decision.base,
        final_bonus=decision.final,
        adjustments=decision.adjustments,
    )
    db.add(analysis)
    db.flush()
    bonus.pay(db, ex, decision.final)
    return analysis


def rating_stats(db: Session, user_ids: list[int]) -> dict[int, tuple[float, int]]:
    if not user_ids:
        return {}
    rows = db.execute(
        select(Review.reviewee_id, func.avg(Review.rating), func.count())
        .where(Review.reviewee_id.in_(user_ids))
        .group_by(Review.reviewee_id)
    ).all()
    return {uid: (round(float(avg), 2), int(n)) for uid, avg, n in rows}


def reviews_of(db: Session, user_id: int, limit: int = 30) -> list[tuple[Review, ReviewAnalysis | None, str, str | None]]:
    rows = db.execute(
        select(Review, ReviewAnalysis, User.nickname, Listing.title)
        .join(User, User.id == Review.reviewer_id)
        .join(Exchange, Exchange.id == Review.exchange_id)
        .outerjoin(Listing, Listing.id == Exchange.listing_id)
        .outerjoin(ReviewAnalysis, ReviewAnalysis.review_id == Review.id)
        .where(Review.reviewee_id == user_id)
        .order_by(Review.created_at.desc())
        .limit(limit)
    ).all()
    return [(r, a, nick, title) for r, a, nick, title in rows]
