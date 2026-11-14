"""숨은 재능 발굴: 세션, 후보, 확정 재능(임베딩)

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-14
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIM = 1024


def _created() -> sa.Column:
    return sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    candidate_status = postgresql.ENUM("pending", "accepted", "edited", "rejected", name="candidate_status")
    talent_source = postgresql.ENUM("ai_confirmed", "manual", name="talent_source")

    op.create_table(
        "discovery_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("intro_text", sa.Text(), nullable=False),
        sa.Column("answers", postgresql.JSONB(), nullable=False),
        sa.Column("encouragement", sa.Text()),
        sa.Column("ai_provider", sa.String(40), nullable=False),
        _created(),
        sa.PrimaryKeyConstraint("id", name="pk_discovery_sessions"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_discovery_sessions_user_id_users"),
    )
    op.create_index("ix_discovery_sessions_user_id", "discovery_sessions", ["user_id"])

    op.create_table(
        "user_talents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("source", talent_source, nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM)),
        sa.Column("embedding_model", sa.String(80)),
        _created(),
        sa.PrimaryKeyConstraint("id", name="pk_user_talents"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_user_talents_user_id_users"),
    )
    op.create_index("ix_user_talents_user_id", "user_talents", ["user_id"])
    # 데이터가 적은 MVP에서는 전체 스캔으로 충분해요. 늘어나면 HNSW 인덱스를 추가해요.

    op.create_table(
        "talent_candidates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("source_quote", sa.Text()),
        sa.Column("confirm_question", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", candidate_status, server_default="pending", nullable=False),
        sa.Column("talent_id", sa.Integer()),
        _created(),
        sa.PrimaryKeyConstraint("id", name="pk_talent_candidates"),
        sa.ForeignKeyConstraint(
            ["session_id"], ["discovery_sessions.id"], name="fk_talent_candidates_session_id_discovery_sessions"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_talent_candidates_user_id_users"),
        sa.ForeignKeyConstraint(
            ["talent_id"], ["user_talents.id"], name="fk_talent_candidates_talent_id_user_talents", ondelete="SET NULL"
        ),
    )
    op.create_index("ix_talent_candidates_session_id", "talent_candidates", ["session_id"])
    op.create_index("ix_talent_candidates_user_id", "talent_candidates", ["user_id"])


def downgrade() -> None:
    op.drop_table("talent_candidates")
    op.drop_table("user_talents")
    op.drop_table("discovery_sessions")
    op.execute("DROP TYPE IF EXISTS talent_source")
    op.execute("DROP TYPE IF EXISTS candidate_status")
