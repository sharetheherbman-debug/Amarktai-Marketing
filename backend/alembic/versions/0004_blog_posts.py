"""add blog_posts table

Revision ID: 0004_blog_posts
Revises: 0003_leads_new_platforms
Create Date: 2026-02-24

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "0004_blog_posts"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "blog_posts",
        sa.Column("id", sa.String(length=255), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("webapp_id", sa.String(length=255), sa.ForeignKey("webapps.id"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=True),
        sa.Column("meta_description", sa.String(length=255), nullable=True),
        sa.Column("sections", sa.JSON(), nullable=True),
        sa.Column("target_keywords", sa.JSON(), nullable=True),
        sa.Column("cta_text", sa.String(length=255), nullable=True),
        sa.Column("cta_url", sa.String(length=255), nullable=True),
        sa.Column("reading_time_mins", sa.String(length=255), nullable=True),
        sa.Column("custom_topic", sa.String(length=255), nullable=True),
        sa.Column("custom_keywords", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=255), nullable=True, server_default="draft"),
        sa.Column("is_published", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("published_url", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_blog_posts_user_id", "blog_posts", ["user_id"])
    op.create_index("ix_blog_posts_slug", "blog_posts", ["slug"])


def downgrade() -> None:
    op.drop_index("ix_blog_posts_slug", table_name="blog_posts")
    op.drop_index("ix_blog_posts_user_id", table_name="blog_posts")
    op.drop_table("blog_posts")
