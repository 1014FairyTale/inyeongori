"""카테고리 이름 변경: '학업·과제' → '공부·학습' (대학생 전용 표현 정리)

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-16
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ["listings", "user_talents", "talent_candidates", "plan_items"]


def upgrade() -> None:
    for t in TABLES:
        op.execute(f"UPDATE {t} SET category = '공부·학습' WHERE category = '학업·과제'")


def downgrade() -> None:
    for t in TABLES:
        op.execute(f"UPDATE {t} SET category = '학업·과제' WHERE category = '공부·학습'")
