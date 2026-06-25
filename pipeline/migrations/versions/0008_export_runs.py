"""Record CSV export metadata and failures.

Revision ID: 0008_export_runs
Revises: 0007_session_review
Create Date: 2026-06-25
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0008_export_runs"
down_revision: str | None = "0007_session_review"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "app_export_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("app_users.id", ondelete="SET NULL"),
        ),
        sa.Column("resource", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("page_size", sa.Integer(), nullable=False),
        sa.Column(
            "filters",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("row_count", sa.Integer()),
        sa.Column("total_rows", sa.Integer()),
        sa.Column("filename", sa.Text()),
        sa.Column("encoding", sa.Text(), nullable=False),
        sa.Column("error_code", sa.Text()),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "resource IN ('sessions', 'events')",
            name="ck_app_export_runs_resource",
        ),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="ck_app_export_runs_status",
        ),
        sa.CheckConstraint(
            "page >= 1 AND page_size BETWEEN 1 AND 1000",
            name="ck_app_export_runs_pagination",
        ),
    )
    with op.get_context().autocommit_block():
        op.create_index(
            "idx_app_export_runs_user_started",
            "app_export_runs",
            ["user_id", "started_at"],
            postgresql_concurrently=True,
        )
        op.create_index(
            "idx_app_export_runs_status_started",
            "app_export_runs",
            ["status", "started_at"],
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    op.drop_table("app_export_runs")
