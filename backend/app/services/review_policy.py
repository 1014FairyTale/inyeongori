"""후기 기한과 이용 제한 (기획자 결정, 2026-11-15).

- 완료된 거래의 요청자는 완료 후 REVIEW_DEADLINE_DAYS(7일) 안에 후기를 써야 해요.
- 기한 안에는 아무 제한이 없어요 (여러 재능을 동시에 요청할 수 있게).
- 기한을 넘긴 후기가 하나라도 있으면 인연고리 이용이 막혀요.
  로그인, 내 정보, 밀린 거래 보기·후기 쓰기만 열려 있고, 후기를 쓰면 바로 풀려요.
- 막힌 사람의 재능 상품은 마켓·매칭에서 빠지고 새 요청도 받을 수 없어요.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, exists, select
from sqlalchemy.orm import Session

from app.core.constants import REVIEW_DEADLINE_DAYS
from app.models import Exchange, ExchangeStatus, Listing, Review, User

DEADLINE = timedelta(days=REVIEW_DEADLINE_DAYS)


@dataclass
class DueReview:
    exchange_id: int
    listing_title: str | None
    provider_nickname: str
    due_at: datetime
    overdue: bool


def due_at(ex: Exchange) -> datetime | None:
    return ex.completed_at + DEADLINE if ex.completed_at else None


def written_on_time(ex: Exchange, review: Review) -> bool:
    d = due_at(ex)
    return d is not None and review.created_at <= d


def _no_review():  # noqa: ANN202
    return ~exists().where(Review.exchange_id == Exchange.id)


def due_reviews(db: Session, user: User, now: datetime | None = None) -> list[DueReview]:
    """내가 써야 하는(아직 안 쓴) 후기 목록. 기한이 가까운 순."""
    now = now or datetime.now(UTC)
    rows = db.execute(
        select(Exchange, Listing.title, User.nickname)
        .outerjoin(Listing, Listing.id == Exchange.listing_id)
        .join(User, User.id == Exchange.provider_id)
        .where(Exchange.requester_id == user.id, Exchange.status == ExchangeStatus.COMPLETED, _no_review())
        .order_by(Exchange.completed_at)
    ).all()
    out = []
    for ex, title, nick in rows:
        d = due_at(ex)
        assert d is not None
        out.append(DueReview(ex.id, title, nick, d, overdue=now > d))
    return out


def is_blocked(db: Session, user: User, now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    return (
        db.scalar(
            select(Exchange.id)
            .where(
                Exchange.requester_id == user.id,
                Exchange.status == ExchangeStatus.COMPLETED,
                Exchange.completed_at < now - DEADLINE,
                _no_review(),
            )
            .limit(1)
        )
        is not None
    )


def blocked_user_ids(now: datetime | None = None) -> Select:
    """기한을 넘긴 후기가 있는 사용자 id (마켓·매칭에서 빼는 데 써요)."""
    now = now or datetime.now(UTC)
    return (
        select(Exchange.requester_id)
        .where(
            Exchange.status == ExchangeStatus.COMPLETED,
            Exchange.completed_at < now - DEADLINE,
            _no_review(),
        )
        .distinct()
    )
