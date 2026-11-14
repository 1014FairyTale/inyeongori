"""숨은 재능 발굴.

discovery_sessions : 온보딩 입력(자기소개·문답) 1회 = 세션 1개
talent_candidates  : AI가 추론한 후보. 사용자가 [맞아요/아니에요/수정]으로 확인해요.
user_talents       : 사용자가 확정한 재능만 저장 + 임베딩(매칭용)
"""

import enum
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

EMBEDDING_DIM = 1024  # bge-m3. 바꾸려면 마이그레이션도 같이 바꿔야 해요.


def _enum(e: type[enum.Enum], name: str) -> Enum:
    return Enum(e, name=name, values_callable=lambda x: [m.value for m in x])


class CandidateStatus(enum.StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EDITED = "edited"
    REJECTED = "rejected"


class TalentSource(enum.StrEnum):
    AI_CONFIRMED = "ai_confirmed"
    MANUAL = "manual"


class DiscoverySession(TimestampMixin, Base):
    __tablename__ = "discovery_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    intro_text: Mapped[str] = mapped_column(Text)
    answers: Mapped[dict[str, Any]] = mapped_column(JSONB)
    encouragement: Mapped[str | None] = mapped_column(Text)
    ai_provider: Mapped[str] = mapped_column(String(40))


class TalentCandidate(TimestampMixin, Base):
    __tablename__ = "talent_candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("discovery_sessions.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    position: Mapped[int]
    name: Mapped[str] = mapped_column(String(40))
    category: Mapped[str] = mapped_column(String(30))
    evidence: Mapped[str] = mapped_column(Text)
    source_quote: Mapped[str | None] = mapped_column(Text)
    confirm_question: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[CandidateStatus] = mapped_column(
        _enum(CandidateStatus, "candidate_status"), default=CandidateStatus.PENDING, server_default="pending"
    )
    talent_id: Mapped[int | None] = mapped_column(ForeignKey("user_talents.id", ondelete="SET NULL"))


class UserTalent(TimestampMixin, Base):
    __tablename__ = "user_talents"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(40))
    category: Mapped[str] = mapped_column(String(30))
    description: Mapped[str | None] = mapped_column(Text)
    source: Mapped[TalentSource] = mapped_column(_enum(TalentSource, "talent_source"))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    embedding_model: Mapped[str | None] = mapped_column(String(80))
