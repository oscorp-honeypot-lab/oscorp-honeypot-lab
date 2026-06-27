"""Add source_mode column to eventos and sessions.

Revision ID: 0016_source_mode
Revises: 0015_lab_runs
Create Date: 2026-06-27
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0016_source_mode"
down_revision: str | None = "0015_lab_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "eventos",
        sa.Column(
            "source_mode",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'lab'"),
        ),
    )
    op.create_check_constraint(
        "ck_eventos_source_mode",
        "eventos",
        "source_mode IN ('lab', 'real')",
    )
    op.add_column(
        "sessions",
        sa.Column(
            "source_mode",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'lab'"),
        ),
    )
    op.create_check_constraint(
        "ck_sessions_source_mode",
        "sessions",
        "source_mode IN ('lab', 'real')",
    )
    with op.get_context().autocommit_block():
        op.create_index(
            "idx_sessions_source_mode",
            "sessions",
            ["source_mode"],
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index(
            "idx_sessions_source_mode",
            table_name="sessions",
            postgresql_concurrently=True,
        )
    op.drop_constraint("ck_sessions_source_mode", "sessions", type_="check")
    op.drop_column("sessions", "source_mode")
    op.drop_constraint("ck_eventos_source_mode", "eventos", type_="check")
    op.drop_column("eventos", "source_mode")
