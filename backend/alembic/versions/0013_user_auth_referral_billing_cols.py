"""Add missing users auth/referral/billing columns.

Revision ID: 0013_user_auth_cols
Revises: 0012_webapp_media_scraper_urls
Create Date: 2026-05-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0013_user_auth_cols"
down_revision: Union[str, None] = "0012_webapp_media_scraper_urls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_cols = {c["name"] for c in inspector.get_columns("users")}
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("users")}
    existing_fks = {fk.get("name") for fk in inspector.get_foreign_keys("users")}

    if "email_verified" not in existing_cols:
        op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=True, server_default=sa.false()))

    if "stripe_customer_id" not in existing_cols:
        op.add_column("users", sa.Column("stripe_customer_id", sa.String(length=255), nullable=True))

    if "referral_code" not in existing_cols:
        op.add_column("users", sa.Column("referral_code", sa.String(length=16), nullable=True))

    if "referred_by" not in existing_cols:
        op.add_column("users", sa.Column("referred_by", sa.String(length=36), nullable=True))

    if "ix_users_referral_code" not in existing_indexes:
        op.create_index("ix_users_referral_code", "users", ["referral_code"], unique=True)

    if "uq_users_stripe_customer_id" not in existing_indexes:
        op.create_index("uq_users_stripe_customer_id", "users", ["stripe_customer_id"], unique=True)

    if "fk_users_referred_by_users" not in existing_fks:
        op.create_foreign_key(
            "fk_users_referred_by_users",
            "users",
            "users",
            ["referred_by"],
            ["id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {c["name"] for c in inspector.get_columns("users")}
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("users")}
    existing_fks = {fk.get("name") for fk in inspector.get_foreign_keys("users")}

    if "fk_users_referred_by_users" in existing_fks:
        op.drop_constraint("fk_users_referred_by_users", "users", type_="foreignkey")

    if "uq_users_stripe_customer_id" in existing_indexes:
        op.drop_index("uq_users_stripe_customer_id", table_name="users")

    if "ix_users_referral_code" in existing_indexes:
        op.drop_index("ix_users_referral_code", table_name="users")

    if "referred_by" in existing_cols:
        op.drop_column("users", "referred_by")
    if "referral_code" in existing_cols:
        op.drop_column("users", "referral_code")
    if "stripe_customer_id" in existing_cols:
        op.drop_column("users", "stripe_customer_id")
    if "email_verified" in existing_cols:
        op.drop_column("users", "email_verified")
