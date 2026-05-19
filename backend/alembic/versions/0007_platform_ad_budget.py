"""Add per-platform ad budget, auto_post/reply flags, and posting_schedule to platform_connections.

Revision ID: 0007_platform_ad_budget
Revises: 0006_user_geolocation
Create Date: 2026-03-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_platform_ad_budget"
down_revision: Union[str, None] = "0006_user_geolocation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "platform_connections",
        sa.Column("monthly_ad_budget", sa.Numeric(10, 2), nullable=True, server_default="0"),
    )
    op.add_column(
        "platform_connections",
        sa.Column("daily_ad_budget", sa.Numeric(10, 2), nullable=True, server_default="0"),
    )
    op.add_column(
        "platform_connections",
        sa.Column("ad_budget_currency", sa.String(length=255), nullable=True, server_default="USD"),
    )
    op.add_column(
        "platform_connections",
        sa.Column("ad_account_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "platform_connections",
        sa.Column("auto_post_enabled", sa.Boolean(), nullable=True, server_default="false"),
    )
    op.add_column(
        "platform_connections",
        sa.Column("auto_reply_enabled", sa.Boolean(), nullable=True, server_default="false"),
    )
    op.add_column(
        "platform_connections",
        sa.Column("posting_schedule", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("platform_connections", "posting_schedule")
    op.drop_column("platform_connections", "auto_reply_enabled")
    op.drop_column("platform_connections", "auto_post_enabled")
    op.drop_column("platform_connections", "ad_account_id")
    op.drop_column("platform_connections", "ad_budget_currency")
    op.drop_column("platform_connections", "daily_ad_budget")
    op.drop_column("platform_connections", "monthly_ad_budget")
