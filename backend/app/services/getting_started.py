"""처음 이용자 '첫 걸음' 체크리스트. 실제로 해 본 것을 데이터에서 확인해서 자동으로 체크돼요."""

from dataclasses import dataclass

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.models import Exchange, ExchangeMessage, Listing, MessageKind, Review, User, UserTalent


@dataclass
class Step:
    key: str
    done: bool


def steps(db: Session, user: User) -> list[Step]:
    def has(stmt) -> bool:  # noqa: ANN001
        return bool(db.scalar(select(exists(stmt))))

    return [
        Step("discover", has(select(UserTalent.id).where(UserTalent.user_id == user.id))),
        Step("list", has(select(Listing.id).where(Listing.provider_id == user.id))),
        Step("request", has(select(Exchange.id).where(Exchange.requester_id == user.id))),
        Step(
            "chat",
            has(
                select(ExchangeMessage.id).where(
                    ExchangeMessage.sender_id == user.id, ExchangeMessage.kind == MessageKind.USER
                )
            ),
        ),
        Step("review", has(select(Review.id).where(Review.reviewer_id == user.id))),
    ]
