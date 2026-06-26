"""Create vt_hash_cache table for VirusTotal hash enrichment.

Revision ID: 0012_vt_hash_cache
Revises: 0011_ip_geo_cache
Create Date: 2026-06-25
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0012_vt_hash_cache"
down_revision: str | None = "0011_ip_geo_cache"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vt_hash_cache",
        sa.Column("sha256", sa.Text(), nullable=False),
        sa.Column("malicious", sa.Integer(), nullable=True),
        sa.Column("suspicious", sa.Integer(), nullable=True),
        sa.Column("undetected", sa.Integer(), nullable=True),
        sa.Column("harmless", sa.Integer(), nullable=True),
        sa.Column("timeout", sa.Integer(), nullable=True),
        sa.Column("last_analysis_date", sa.BigInteger(), nullable=True),
        sa.Column("reputation", sa.Integer(), nullable=True),
        sa.Column(
            "queried_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("sha256"),
    )
    op.create_index("idx_vt_hash_cache_expires_at", "vt_hash_cache", ["expires_at"])


def downgrade() -> None:
    op.drop_index("idx_vt_hash_cache_expires_at", table_name="vt_hash_cache")
    op.drop_table("vt_hash_cache")
