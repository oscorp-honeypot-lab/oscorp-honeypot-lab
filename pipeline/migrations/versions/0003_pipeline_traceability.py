"""Add pipeline traceability and event error quarantine.

Revision ID: 0003_pipeline_traceability
Revises: 0002_pipeline_checkpoints
Create Date: 2026-06-25
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_pipeline_traceability"
down_revision: str | None = "0002_pipeline_checkpoints"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("pipeline_runs", sa.Column("request_id", sa.Text()))
    op.add_column("pipeline_runs", sa.Column("triggered_by", sa.Text()))
    op.add_column(
        "pipeline_runs",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column("pipeline_runs", sa.Column("error_code", sa.Text()))
    op.add_column("pipeline_runs", sa.Column("error_detail", sa.Text()))
    op.create_index(
        "uq_pipeline_runs_request_id",
        "pipeline_runs",
        ["request_id"],
        unique=True,
    )

    op.create_table(
        "pipeline_event_errors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "run_id",
            sa.Integer(),
            sa.ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_key", sa.Text(), nullable=False),
        sa.Column("line_number", sa.BigInteger(), nullable=False),
        sa.Column("byte_offset", sa.BigInteger(), nullable=False),
        sa.Column("error_code", sa.Text(), nullable=False),
        sa.Column("error_detail", sa.Text(), nullable=False),
        sa.Column("raw_line", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "idx_pipeline_event_errors_run_id",
        "pipeline_event_errors",
        ["run_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_pipeline_event_errors_run_id",
        table_name="pipeline_event_errors",
    )
    op.drop_table("pipeline_event_errors")
    op.drop_index("uq_pipeline_runs_request_id", table_name="pipeline_runs")
    op.drop_column("pipeline_runs", "error_detail")
    op.drop_column("pipeline_runs", "error_code")
    op.drop_column("pipeline_runs", "attempt_count")
    op.drop_column("pipeline_runs", "triggered_by")
    op.drop_column("pipeline_runs", "request_id")
