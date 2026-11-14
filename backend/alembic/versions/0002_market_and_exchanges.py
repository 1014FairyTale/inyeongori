"""재능 마켓, 거래, 합의서

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-14
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LISTING_STATUS = ("active", "paused")
EXCHANGE_STATUS = ("requested", "accepted", "cancel_requested", "completed", "cancelled", "rejected")


def _ts(name: str, nullable: bool = True) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=nullable)


def upgrade() -> None:
    listing_status = postgresql.ENUM(*LISTING_STATUS, name="listing_status")
    exchange_status = postgresql.ENUM(*EXCHANGE_STATUS, name="exchange_status")

    op.create_table(
        "listings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("price_tokens", sa.Integer(), nullable=False),
        sa.Column("est_minutes", sa.Integer()),
        sa.Column("status", listing_status, server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_listings"),
        sa.ForeignKeyConstraint(["provider_id"], ["users.id"], name="fk_listings_provider_id_users"),
        sa.CheckConstraint("price_tokens > 0", name="ck_listings_price_positive"),
    )
    op.create_index("ix_listings_provider_id", "listings", ["provider_id"])
    op.create_index("ix_listings_category", "listings", ["category"])

    op.create_table(
        "exchanges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("listing_id", sa.Integer()),
        sa.Column("requester_id", sa.Integer(), nullable=False),
        sa.Column("provider_id", sa.Integer(), nullable=False),
        sa.Column("price_tokens", sa.Integer(), nullable=False),
        sa.Column("status", exchange_status, server_default="requested", nullable=False),
        _ts("requester_done_at"),
        _ts("provider_done_at"),
        sa.Column("cancel_requested_by", sa.Integer()),
        sa.Column("cancelled_by", sa.Integer()),
        _ts("accepted_at"),
        _ts("completed_at"),
        _ts("closed_at"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_exchanges"),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], name="fk_exchanges_listing_id_listings"),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"], name="fk_exchanges_requester_id_users"),
        sa.ForeignKeyConstraint(["provider_id"], ["users.id"], name="fk_exchanges_provider_id_users"),
        sa.ForeignKeyConstraint(["cancel_requested_by"], ["users.id"], name="fk_exchanges_cancel_requested_by_users"),
        sa.ForeignKeyConstraint(["cancelled_by"], ["users.id"], name="fk_exchanges_cancelled_by_users"),
        sa.CheckConstraint("price_tokens > 0", name="ck_exchanges_price_positive"),
        sa.CheckConstraint("requester_id <> provider_id", name="ck_exchanges_distinct_parties"),
    )
    op.create_index("ix_exchanges_listing_id", "exchanges", ["listing_id"])
    op.create_index("ix_exchanges_requester_id", "exchanges", ["requester_id"])
    op.create_index("ix_exchanges_provider_id", "exchanges", ["provider_id"])

    op.create_table(
        "agreements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("exchange_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("proposed_by", sa.Integer(), nullable=False),
        sa.Column("terms", postgresql.JSONB(), nullable=False),
        sa.Column("ai_generated", sa.Boolean(), server_default="false", nullable=False),
        _ts("requester_agreed_at"),
        _ts("provider_agreed_at"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_agreements"),
        sa.ForeignKeyConstraint(["exchange_id"], ["exchanges.id"], name="fk_agreements_exchange_id_exchanges"),
        sa.ForeignKeyConstraint(["proposed_by"], ["users.id"], name="fk_agreements_proposed_by_users"),
        sa.UniqueConstraint("exchange_id", "version", name="uq_agreements_exchange_version"),
    )
    op.create_index("ix_agreements_exchange_id", "agreements", ["exchange_id"])

    op.create_foreign_key(
        "fk_ledger_transfers_exchange_id_exchanges", "ledger_transfers", "exchanges", ["exchange_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_ledger_transfers_exchange_id_exchanges", "ledger_transfers", type_="foreignkey")
    op.drop_table("agreements")
    op.drop_table("exchanges")
    op.drop_table("listings")
    op.execute("DROP TYPE IF EXISTS exchange_status")
    op.execute("DROP TYPE IF EXISTS listing_status")
