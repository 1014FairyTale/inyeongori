"""후기와 AI 후기 분석

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-14
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _created() -> sa.Column:
    return sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("exchange_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), nullable=False),
        sa.Column("reviewee_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("good_text", sa.Text(), nullable=False),
        sa.Column("bad_text", sa.Text()),
        _created(),
        sa.PrimaryKeyConstraint("id", name="pk_reviews"),
        sa.ForeignKeyConstraint(["exchange_id"], ["exchanges.id"], name="fk_reviews_exchange_id_exchanges"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], name="fk_reviews_reviewer_id_users"),
        sa.ForeignKeyConstraint(["reviewee_id"], ["users.id"], name="fk_reviews_reviewee_id_users"),
        sa.UniqueConstraint("exchange_id", name="uq_reviews_exchange_id"),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating_range"),
    )
    op.create_index("ix_reviews_reviewer_id", "reviews", ["reviewer_id"])
    op.create_index("ix_reviews_reviewee_id", "reviews", ["reviewee_id"])

    op.create_table(
        "review_analyses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("reviewee_id", sa.Integer(), nullable=False),
        sa.Column("contribution_score", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("reasons", postgresql.JSONB(), nullable=False),
        sa.Column("flags", postgresql.JSONB(), nullable=False),
        sa.Column("ai_provider", sa.String(60), nullable=False),
        sa.Column("eligible", sa.Boolean(), nullable=False),
        sa.Column("base_bonus", sa.Integer(), nullable=False),
        sa.Column("final_bonus", sa.Integer(), nullable=False),
        sa.Column("adjustments", postgresql.JSONB(), nullable=False),
        _created(),
        sa.PrimaryKeyConstraint("id", name="pk_review_analyses"),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], name="fk_review_analyses_review_id_reviews"),
        sa.ForeignKeyConstraint(["reviewee_id"], ["users.id"], name="fk_review_analyses_reviewee_id_users"),
        sa.UniqueConstraint("review_id", name="uq_review_analyses_review_id"),
    )
    op.create_index("ix_review_analyses_reviewee_id", "review_analyses", ["reviewee_id"])


def downgrade() -> None:
    op.drop_table("review_analyses")
    op.drop_table("reviews")
