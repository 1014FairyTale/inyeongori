"""후기와 AI 후기 분석 (기능 8)."""

from typing import Any

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Review(TimestampMixin, Base):
    __tablename__ = "reviews"
    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    exchange_id: Mapped[int] = mapped_column(ForeignKey("exchanges.id"), unique=True)  # 거래당 후기 1개
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)  # 요청자
    reviewee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)  # 제공자
    rating: Mapped[int] = mapped_column(Integer)
    good_text: Mapped[str] = mapped_column(Text)
    bad_text: Mapped[str | None] = mapped_column(Text)


class ReviewAnalysis(TimestampMixin, Base):
    """AI 판단(점수·근거)과 규칙에 따른 보너스 계산 과정을 모두 남겨요."""

    __tablename__ = "review_analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id"), unique=True)
    reviewee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    contribution_score: Mapped[int] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(Text)
    reasons: Mapped[list[str]] = mapped_column(JSONB)  # AI 판단 근거
    flags: Mapped[list[str]] = mapped_column(JSONB)  # AI가 찾은 주의점 (짧음, 별점과 내용 불일치 등)
    ai_provider: Mapped[str] = mapped_column(String(60))
    eligible: Mapped[bool] = mapped_column(Boolean)
    base_bonus: Mapped[int] = mapped_column(Integer)  # 상한·감액 전
    final_bonus: Mapped[int] = mapped_column(Integer)  # 실제 지급
    adjustments: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)  # 적용된 규칙 기록
    # 후기 작성자(요청자) 쪽: 후기 성의 점수와 10% 환급
    review_quality: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    review_quality_reason: Mapped[str | None] = mapped_column(Text)
    reviewer_reward: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    reviewer_reward_note: Mapped[str | None] = mapped_column(Text)
