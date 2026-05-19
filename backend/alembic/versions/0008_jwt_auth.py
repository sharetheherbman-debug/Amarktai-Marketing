"""Add hashed_password to users table (app-owned JWT auth).

Revision ID: 0008_jwt_auth
Revises: 0007_platform_ad_budget
Create Date: 2026-03-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0008_jwt_auth"
down_revision: Union[str, None] = "0007_platform_ad_budget"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("hashed_password", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "hashed_password")
