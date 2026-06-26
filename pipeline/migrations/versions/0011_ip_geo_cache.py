"""Create ip_geo_cache table for geographic IP enrichment.

Revision ID: 0011_ip_geo_cache
Revises: 0010_alert_attempt_count
Create Date: 2026-06-25
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0011_ip_geo_cache"
down_revision: str | None = "0010_alert_attempt_count"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ip_geo_cache",
        sa.Column("ip", sa.Text(), nullable=False),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column("country_code", sa.Text(), nullable=True),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("isp", sa.Text(), nullable=True),
        sa.Column("asn", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column(
            "queried_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("ip"),
    )
    op.create_index("idx_ip_geo_cache_expires_at", "ip_geo_cache", ["expires_at"])


def downgrade() -> None:
    op.drop_index("idx_ip_geo_cache_expires_at", table_name="ip_geo_cache")
    op.drop_table("ip_geo_cache")
