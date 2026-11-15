"""토큰 원장.

- token_accounts: 사용자마다 available(사용 가능) / escrow(보류 중) 계정 2개,
  시스템 사용자에게 system_issuance(발행) / system_bonus_pool(보너스 풀) 계정.
  balance는 원장 합계의 캐시이고, 발행 계정을 빼면 CHECK로 음수를 막아요.
- ledger_transfers: 모든 증감 기록. 한 행 = from 계정에서 to 계정으로 amount만큼 이동.
  잔액은 반드시 services/ledger.py 의 transfer()로만 바꿔요.
"""

import enum
import uuid

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AccountKind(enum.StrEnum):
    AVAILABLE = "available"
    ESCROW = "escrow"
    SYSTEM_ISSUANCE = "system_issuance"
    SYSTEM_BONUS_POOL = "system_bonus_pool"


class EntryType(enum.StrEnum):
    SYSTEM_FUNDING = "system_funding"  # 발행 계정 → 보너스 풀 (초기 적립)
    SIGNUP_BONUS = "signup_bonus"  # 가입 보너스
    ESCROW_HOLD = "escrow_hold"  # 결제 보류
    PAYOUT = "payout"  # 지급
    REFUND = "refund"  # 환불
    REVIEW_BONUS = "review_bonus"  # 후기 보너스 (제공자)
    REVIEW_REWARD = "review_reward"  # 성의 있는 후기 환급 (요청자, 거래가의 10%)
    CERT_BONUS = "cert_bonus"  # 인증 보너스 (선택 기능)


def _enum(e: type[enum.Enum], name: str) -> Enum:
    return Enum(e, name=name, values_callable=lambda x: [m.value for m in x])


class TokenAccount(TimestampMixin, Base):
    __tablename__ = "token_accounts"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "kind", name="uq_token_accounts_owner_kind"),
        CheckConstraint(
            "balance >= 0 OR kind = 'system_issuance'", name="balance_non_negative"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[AccountKind] = mapped_column(_enum(AccountKind, "account_kind"))
    balance: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")


class LedgerTransfer(TimestampMixin, Base):
    __tablename__ = "ledger_transfers"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("from_account_id <> to_account_id", name="distinct_accounts"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_type: Mapped[EntryType] = mapped_column(_enum(EntryType, "entry_type"))
    from_account_id: Mapped[int] = mapped_column(ForeignKey("token_accounts.id"), index=True)
    to_account_id: Mapped[int] = mapped_column(ForeignKey("token_accounts.id"), index=True)
    amount: Mapped[int] = mapped_column(BigInteger)
    exchange_id: Mapped[int | None] = mapped_column(ForeignKey("exchanges.id"), index=True)
    # 같은 이동이 두 번 기록되지 않게 (예: "signup:12", "payout:34")
    idempotency_key: Mapped[str] = mapped_column(String(120), unique=True)
    memo: Mapped[str | None] = mapped_column(String(200))
