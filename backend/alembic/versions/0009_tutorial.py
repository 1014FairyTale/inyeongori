"""처음 이용자 튜토리얼을 본 시각

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("tutorial_seen_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("users", "tutorial_seen_at")
