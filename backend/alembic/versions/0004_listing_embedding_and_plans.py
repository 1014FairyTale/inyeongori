"""상품 임베딩, 부탁 쪼개기·목표 경로 계획

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-14
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("embedding", Vector(1024)))
    op.add_column("listings", sa.Column("embedding_model", sa.String(80)))

    plan_kind = postgresql.ENUM("breakdown", "path", name="plan_kind")
    price_basis = postgresql.ENUM("market", "ai", "user", name="price_basis")

    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("kind", plan_kind, nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_plans"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_plans_user_id_users"),
    )
    op.create_index("ix_plans_user_id", "plans", ["user_id"])

    op.create_table(
        "plan_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(60), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("minutes", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("suggested_tokens", sa.Integer(), nullable=False),
        sa.Column("price_basis", price_basis, nullable=False),
        sa.Column("similar_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("linked_listing_id", sa.Integer()),
        sa.Column("ai_generated", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("edited", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_plan_items"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], name="fk_plan_items_plan_id_plans", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["linked_listing_id"], ["listings.id"], name="fk_plan_items_linked_listing_id_listings", ondelete="SET NULL"
        ),
    )
    op.create_index("ix_plan_items_plan_id", "plan_items", ["plan_id"])


def downgrade() -> None:
    op.drop_table("plan_items")
    op.drop_table("plans")
    op.execute("DROP TYPE IF EXISTS price_basis")
    op.execute("DROP TYPE IF EXISTS plan_kind")
    op.drop_column("listings", "embedding_model")
    op.drop_column("listings", "embedding")
