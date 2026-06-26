"""Create lab simulation run storage.

Revision ID: 0015_lab_runs
Revises: 0014_report_deliveries
Create Date: 2026-06-26
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0015_lab_runs"
down_revision: str | None = "0014_report_deliveries"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lab_runs",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column("scenario", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'queued'"),
        ),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("exit_code", sa.Integer()),
        sa.Column("log_text", sa.Text()),
        sa.Column("error_detail", sa.Text()),
        sa.Column("pipeline_events_read", sa.Integer()),
        sa.Column("pipeline_errors", sa.Integer()),
        sa.CheckConstraint(
            "scenario IN ('brute-force', 'recon', 'malware-download', 'full')",
            name="ck_lab_runs_scenario",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'processing', 'completed', 'failed')",
            name="ck_lab_runs_status",
        ),
    )
    with op.get_context().autocommit_block():
        op.create_index(
            "idx_lab_runs_status_started",
            "lab_runs",
            ["status", "started_at"],
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index(
            "idx_lab_runs_status_started",
            table_name="lab_runs",
            postgresql_concurrently=True,
        )
    op.drop_table("lab_runs")
