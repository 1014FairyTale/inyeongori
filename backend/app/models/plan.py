"""부탁 쪼개기(breakdown)와 목표 기반 교환 경로(path, 6단계)."""

import enum

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


def _enum(e: type[enum.Enum], name: str) -> Enum:
    return Enum(e, name=name, values_callable=lambda x: [m.value for m in x])


class PlanKind(enum.StrEnum):
    BREAKDOWN = "breakdown"
    PATH = "path"


class PriceBasis(enum.StrEnum):
    MARKET = "market"  # 비슷한 상품 가격의 중앙값
    AI = "ai"  # 비슷한 상품이 부족해서 AI가 추정
    USER = "user"  # 사용자가 직접 수정


class Plan(TimestampMixin, Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    goal: Mapped[str] = mapped_column(Text)
    kind: Mapped[PlanKind] = mapped_column(_enum(PlanKind, "plan_kind"))
    summary: Mapped[str | None] = mapped_column(Text)


class PlanItem(TimestampMixin, Base):
    __tablename__ = "plan_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(60))
    description: Mapped[str | None] = mapped_column(Text)
    minutes: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(30))
    suggested_tokens: Mapped[int] = mapped_column(Integer)
    price_basis: Mapped[PriceBasis] = mapped_column(_enum(PriceBasis, "price_basis"))
    similar_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    linked_listing_id: Mapped[int | None] = mapped_column(ForeignKey("listings.id", ondelete="SET NULL"))
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    edited: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
