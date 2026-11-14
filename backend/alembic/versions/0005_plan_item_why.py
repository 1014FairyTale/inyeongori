"""목표 경로 단계의 '왜 필요한지'

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-14
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("plan_items", sa.Column("why", sa.Text()))


def downgrade() -> None:
    op.drop_column("plan_items", "why")
