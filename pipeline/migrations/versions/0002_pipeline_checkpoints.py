"""Add persistent pipeline checkpoints.

Revision ID: 0002_pipeline_checkpoints
Revises: 0001_initial_schema
Create Date: 2026-06-25
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_pipeline_checkpoints"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pipeline_checkpoints",
        sa.Column("source_key", sa.Text(), primary_key=True),
        sa.Column("file_device", sa.BigInteger()),
        sa.Column("file_inode", sa.BigInteger()),
        sa.Column("fingerprint_hash", sa.Text(), nullable=False),
        sa.Column("fingerprint_bytes", sa.Integer(), nullable=False),
        sa.Column("byte_offset", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("line_number", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("file_size", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("last_run_id", sa.Integer()),
        sa.Column("reset_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_reset_reason", sa.Text()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["last_run_id"],
            ["pipeline_runs.id"],
            ondelete="SET NULL",
        ),
    )

    op.add_column("pipeline_runs", sa.Column("source_key", sa.Text()))
    op.add_column("pipeline_runs", sa.Column("mode", sa.Text()))
    op.add_column(
        "pipeline_runs",
        sa.Column("source_offset_start", sa.BigInteger()),
    )
    op.add_column(
        "pipeline_runs",
        sa.Column("source_offset_end", sa.BigInteger()),
    )
    op.add_column(
        "pipeline_runs",
        sa.Column("checkpoint_reset_reason", sa.Text()),
    )


def downgrade() -> None:
    op.drop_column("pipeline_runs", "checkpoint_reset_reason")
    op.drop_column("pipeline_runs", "source_offset_end")
    op.drop_column("pipeline_runs", "source_offset_start")
    op.drop_column("pipeline_runs", "mode")
    op.drop_column("pipeline_runs", "source_key")
    op.drop_table("pipeline_checkpoints")
