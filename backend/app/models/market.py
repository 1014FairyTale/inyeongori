"""재능 마켓과 거래.

거래 상태 흐름 (README 결정 사항 D6)
  requested ──(양측이 현재 합의서에 동의)──▶ accepted [요청자 토큰 보류]
  requested ──(제공자 거절)──▶ rejected / (요청자 철회)──▶ cancelled      [토큰 이동 없음]
  accepted ──(양측 완료 확인)──▶ completed [제공자에게 지급]
  accepted ──(제공자 취소)──▶ cancelled [요청자에게 환불]
  accepted ──(요청자 취소 요청)──▶ cancel_requested ──(제공자 승인)──▶ cancelled [환불]
                                                  └─(제공자 거절)──▶ accepted
"""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


def _enum(e: type[enum.Enum], name: str) -> Enum:
    return Enum(e, name=name, values_callable=lambda x: [m.value for m in x])


class ListingStatus(enum.StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"


class ExchangeStatus(enum.StrEnum):
    REQUESTED = "requested"
    ACCEPTED = "accepted"
    CANCEL_REQUESTED = "cancel_requested"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class Listing(TimestampMixin, Base):
    __tablename__ = "listings"
    __table_args__ = (CheckConstraint("price_tokens > 0", name="price_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(30), index=True)
    price_tokens: Mapped[int] = mapped_column(Integer)
    est_minutes: Mapped[int | None] = mapped_column(Integer)  # 참고용 (가격과 무관)
    status: Mapped[ListingStatus] = mapped_column(
        _enum(ListingStatus, "listing_status"), default=ListingStatus.ACTIVE, server_default="active"
    )


class Exchange(TimestampMixin, Base):
    __tablename__ = "exchanges"
    __table_args__ = (
        CheckConstraint("price_tokens > 0", name="price_positive"),
        CheckConstraint("requester_id <> provider_id", name="distinct_parties"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int | None] = mapped_column(ForeignKey("listings.id"), index=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    price_tokens: Mapped[int] = mapped_column(Integer)  # 요청 시점 가격 스냅샷
    status: Mapped[ExchangeStatus] = mapped_column(
        _enum(ExchangeStatus, "exchange_status"), default=ExchangeStatus.REQUESTED, server_default="requested"
    )
    requester_done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_requested_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    cancelled_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # 취소·거절 시각


class Agreement(TimestampMixin, Base):
    """교환 범위 합의서. 조건을 바꾸면 version이 올라가고 상대방이 다시 동의해야 해요."""

    __tablename__ = "agreements"
    __table_args__ = (UniqueConstraint("exchange_id", "version", name="uq_agreements_exchange_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    exchange_id: Mapped[int] = mapped_column(ForeignKey("exchanges.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    proposed_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    terms: Mapped[dict[str, Any]] = mapped_column(JSONB)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    requester_agreed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_agreed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
