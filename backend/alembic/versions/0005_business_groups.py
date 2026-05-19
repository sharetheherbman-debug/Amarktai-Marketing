"""Add business_groups table and scraped_data to webapps

Revision ID: 0005_business_groups
Revises: 0004_blog_posts
Create Date: 2026-02-24
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0005_business_groups"
down_revision = "0004_blog_posts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add scraped_data JSON column to webapps
    op.add_column("webapps", sa.Column("scraped_data", sa.JSON(), nullable=True))

    # Create business_groups table
    op.create_table(
        "business_groups",
        sa.Column("id", sa.String(length=255), primary_key=True, index=True),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("webapp_id", sa.String(length=255), sa.ForeignKey("webapps.id"), nullable=False, index=True),
        sa.Column(
            "platform",
            sa.Enum("facebook", "reddit", "telegram", "discord", "linkedin", name="groupplatform"),
            nullable=False,
        ),
        sa.Column("group_id", sa.String(length=255), nullable=True),
        sa.Column("group_name", sa.String(length=255), nullable=False),
        sa.Column("group_url", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("suggested", "joined", "active", "paused", "removed", name="groupstatus"),
            nullable=False,
            server_default="suggested",
        ),
        sa.Column("member_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("posts_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_engagements", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_leads", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_interaction_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("keywords_used", sa.String(length=255), nullable=True),
        sa.Column("compliance_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("business_groups")
    op.drop_column("webapps", "scraped_data")
    op.execute("DROP TYPE IF EXISTS groupstatus")
    op.execute("DROP TYPE IF EXISTS groupplatform")
