"""후기 작성자 성의 점수·10% 환급

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 새 enum 값은 같은 트랜잭션 안에서 쓰지만 않으면 돼요 (이 마이그레이션에서는 쓰지 않아요)
    op.execute("ALTER TYPE entry_type ADD VALUE IF NOT EXISTS 'review_reward'")
    op.add_column("review_analyses", sa.Column("review_quality", sa.Integer(), server_default="0", nullable=False))
    op.add_column("review_analyses", sa.Column("review_quality_reason", sa.Text()))
    op.add_column("review_analyses", sa.Column("reviewer_reward", sa.Integer(), server_default="0", nullable=False))
    op.add_column("review_analyses", sa.Column("reviewer_reward_note", sa.Text()))
    op.create_index("ix_exchanges_requester_completed", "exchanges", ["requester_id", "status", "completed_at"])


def downgrade() -> None:
    op.drop_index("ix_exchanges_requester_completed", table_name="exchanges")
    op.drop_column("review_analyses", "reviewer_reward_note")
    op.drop_column("review_analyses", "reviewer_reward")
    op.drop_column("review_analyses", "review_quality_reason")
    op.drop_column("review_analyses", "review_quality")
    # PostgreSQL은 enum 값을 지울 수 없어서 review_reward 값은 남겨 둬요
