"""회원과 토큰 원장

Revision ID: 0001
Revises:
Create Date: 2026-11-14
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACCOUNT_KINDS = ("available", "escrow", "system_issuance", "system_bonus_pool")
ENTRY_TYPES = (
    "system_funding",
    "signup_bonus",
    "escrow_hold",
    "payout",
    "refund",
    "review_bonus",
    "cert_bonus",
)


def upgrade() -> None:
    # 4단계(임베딩)에서 쓸 pgvector 확장을 미리 켜 둬요
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("nickname", sa.String(40), nullable=False),
        sa.Column("school", sa.String(80)),
        sa.Column("major", sa.String(80)),
        sa.Column("bio", sa.Text()),
        sa.Column("is_system", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_admin", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    account_kind = postgresql.ENUM(*ACCOUNT_KINDS, name="account_kind")
    entry_type = postgresql.ENUM(*ENTRY_TYPES, name="entry_type")

    op.create_table(
        "token_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("kind", account_kind, nullable=False),
        sa.Column("balance", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_token_accounts"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], name="fk_token_accounts_owner_user_id_users"),
        sa.UniqueConstraint("owner_user_id", "kind", name="uq_token_accounts_owner_kind"),
        sa.CheckConstraint(
            "balance >= 0 OR kind = 'system_issuance'",
            name="ck_token_accounts_balance_non_negative",
        ),
    )
    op.create_index("ix_token_accounts_owner_user_id", "token_accounts", ["owner_user_id"])

    op.create_table(
        "ledger_transfers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entry_type", entry_type, nullable=False),
        sa.Column("from_account_id", sa.Integer(), nullable=False),
        sa.Column("to_account_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("exchange_id", sa.Integer()),
        sa.Column("idempotency_key", sa.String(120), nullable=False),
        sa.Column("memo", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_ledger_transfers"),
        sa.ForeignKeyConstraint(
            ["from_account_id"], ["token_accounts.id"], name="fk_ledger_transfers_from_account_id_token_accounts"
        ),
        sa.ForeignKeyConstraint(
            ["to_account_id"], ["token_accounts.id"], name="fk_ledger_transfers_to_account_id_token_accounts"
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_ledger_transfers_idempotency_key"),
        sa.CheckConstraint("amount > 0", name="ck_ledger_transfers_amount_positive"),
        sa.CheckConstraint("from_account_id <> to_account_id", name="ck_ledger_transfers_distinct_accounts"),
    )
    op.create_index("ix_ledger_transfers_from_account_id", "ledger_transfers", ["from_account_id"])
    op.create_index("ix_ledger_transfers_to_account_id", "ledger_transfers", ["to_account_id"])
    op.create_index("ix_ledger_transfers_exchange_id", "ledger_transfers", ["exchange_id"])


def downgrade() -> None:
    op.drop_table("ledger_transfers")
    op.drop_table("token_accounts")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS entry_type")
    op.execute("DROP TYPE IF EXISTS account_kind")
