"""Create periodic report run storage.

Revision ID: 0013_report_runs
Revises: 0012_vt_hash_cache
Create Date: 2026-06-26
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0013_report_runs"
down_revision: str | None = "0012_vt_hash_cache"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "pipeline_run_id",
            sa.Integer(),
            sa.ForeignKey("pipeline_runs.id", ondelete="SET NULL"),
        ),
        sa.Column("period_type", sa.Text(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "dataset",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error_code", sa.Text()),
        sa.Column("error_detail", sa.Text()),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "period_type IN ('daily', 'weekly')",
            name="ck_report_runs_period_type",
        ),
        sa.CheckConstraint(
            "status IN ('completed', 'failed')",
            name="ck_report_runs_status",
        ),
        sa.CheckConstraint(
            "period_start < period_end",
            name="ck_report_runs_period_order",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(dataset) = 'object'",
            name="ck_report_runs_dataset_object",
        ),
    )
    with op.get_context().autocommit_block():
        op.create_index(
            "uq_report_runs_period",
            "report_runs",
            ["period_type", "period_start", "period_end"],
            unique=True,
            postgresql_concurrently=True,
        )
        op.create_index(
            "idx_report_runs_status_started",
            "report_runs",
            ["status", "started_at"],
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index(
            "idx_report_runs_status_started",
            table_name="report_runs",
            postgresql_concurrently=True,
        )
        op.drop_index(
            "uq_report_runs_period",
            table_name="report_runs",
            postgresql_concurrently=True,
        )
    op.drop_table("report_runs")
