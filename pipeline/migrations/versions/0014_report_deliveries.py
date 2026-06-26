"""Record report downloads and deliveries.

Revision ID: 0014_report_deliveries
Revises: 0013_report_runs
Create Date: 2026-06-26
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0014_report_deliveries"
down_revision: str | None = "0013_report_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_deliveries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "report_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("report_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("app_users.id", ondelete="SET NULL"),
        ),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("format", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("filename", sa.Text()),
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
            "channel IN ('download', 'telegram')",
            name="ck_report_deliveries_channel",
        ),
        sa.CheckConstraint(
            "format IN ('html', 'csv')",
            name="ck_report_deliveries_format",
        ),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'failed', 'skipped')",
            name="ck_report_deliveries_status",
        ),
    )
    with op.get_context().autocommit_block():
        op.create_index(
            "idx_report_deliveries_report_started",
            "report_deliveries",
            ["report_run_id", "started_at"],
            postgresql_concurrently=True,
        )
        op.create_index(
            "idx_report_deliveries_status_started",
            "report_deliveries",
            ["status", "started_at"],
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index(
            "idx_report_deliveries_status_started",
            table_name="report_deliveries",
            postgresql_concurrently=True,
        )
        op.drop_index(
            "idx_report_deliveries_report_started",
            table_name="report_deliveries",
            postgresql_concurrently=True,
        )
    op.drop_table("report_deliveries")
