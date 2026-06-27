"""Persist versioned session risk scores.

Revision ID: 0005_session_risk_scores
Revises: 0004_correlated_sessions
Create Date: 2026-06-25
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_session_risk_scores"
down_revision: str | None = "0004_correlated_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "session_risk_scores",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_key",
            sa.Text(),
            sa.ForeignKey("sessions.session_key", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rules_version", sa.Text(), nullable=False),
        sa.Column("score", sa.SmallInteger(), nullable=False),
        sa.Column("risk_level", sa.Text(), nullable=False),
        sa.Column(
            "reasons",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint(
            "session_key",
            "rules_version",
            name="uq_session_risk_scores_session_version",
        ),
        sa.CheckConstraint(
            "score BETWEEN 0 AND 100",
            name="ck_session_risk_scores_score",
        ),
        sa.CheckConstraint(
            "risk_level IN ('low', 'medium', 'high', 'critical')",
            name="ck_session_risk_scores_level",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(reasons) = 'array'",
            name="ck_session_risk_scores_reasons",
        ),
    )

    with op.get_context().autocommit_block():
        op.create_index(
            "idx_session_risk_scores_version_level",
            "session_risk_scores",
            ["rules_version", "risk_level"],
            postgresql_concurrently=True,
        )
        op.create_index(
            "idx_session_risk_scores_version_score",
            "session_risk_scores",
            ["rules_version", "score"],
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    op.drop_table("session_risk_scores")
