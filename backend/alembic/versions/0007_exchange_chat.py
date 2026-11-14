"""거래 채팅

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    message_kind = postgresql.ENUM("user", "system", name="message_kind")
    op.create_table(
        "exchange_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("exchange_id", sa.Integer(), nullable=False),
        sa.Column("sender_id", sa.Integer()),
        sa.Column("kind", message_kind, server_default="user", nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_exchange_messages"),
        sa.ForeignKeyConstraint(["exchange_id"], ["exchanges.id"], name="fk_exchange_messages_exchange_id_exchanges"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], name="fk_exchange_messages_sender_id_users"),
        sa.CheckConstraint("(kind = 'system') OR (sender_id IS NOT NULL)", name="ck_exchange_messages_user_has_sender"),
    )
    op.create_index("ix_exchange_messages_exchange_id_id", "exchange_messages", ["exchange_id", "id"])
    op.add_column("exchanges", sa.Column("requester_last_read_id", sa.Integer()))
    op.add_column("exchanges", sa.Column("provider_last_read_id", sa.Integer()))


def downgrade() -> None:
    op.drop_column("exchanges", "provider_last_read_id")
    op.drop_column("exchanges", "requester_last_read_id")
    op.drop_table("exchange_messages")
    op.execute("DROP TYPE IF EXISTS message_kind")
