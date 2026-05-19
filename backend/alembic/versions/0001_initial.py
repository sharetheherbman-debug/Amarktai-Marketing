"""Initial schema – all tables

Revision ID: 0001_initial
Revises: 
Create Date: 2026-02-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("avatar", sa.String(length=255), nullable=True),
        sa.Column("plan", sa.String(length=255), nullable=True),
        sa.Column("monthly_content_quota", sa.Integer(), nullable=True),
        sa.Column("monthly_content_used", sa.Integer(), nullable=True),
        sa.Column("api_cost_budget", sa.String(length=255), nullable=True),
        sa.Column("api_cost_used", sa.String(length=255), nullable=True),
        sa.Column("auto_post_enabled", sa.Boolean(), nullable=True),
        sa.Column("auto_reply_enabled", sa.Boolean(), nullable=True),
        sa.Column("low_risk_auto_reply", sa.Boolean(), nullable=True),
        sa.Column("preferred_language", sa.String(length=255), nullable=True),
        sa.Column("timezone", sa.String(length=255), nullable=True),
        sa.Column("notification_preferences", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_id", "users", ["id"], unique=False)

    # webapps
    op.create_table(
        "webapps",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("target_audience", sa.String(length=255), nullable=True),
        sa.Column("key_features", sa.JSON(), nullable=True),
        sa.Column("logo", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webapps_id", "webapps", ["id"], unique=False)

    # platform_connections
    op.create_table(
        "platform_connections",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("platform", sa.String(length=255), nullable=False),
        sa.Column("account_name", sa.String(length=255), nullable=False),
        sa.Column("account_id", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ab_tests (must come before content for FK)
    op.create_table(
        "ab_tests",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=255), nullable=True),
        sa.Column("variants", sa.JSON(), nullable=True),
        sa.Column("variant_metrics", sa.JSON(), nullable=True),
        sa.Column("winning_variant_id", sa.String(length=255), nullable=True),
        sa.Column("confidence_level", sa.String(length=255), nullable=True),
        sa.Column("improvement_percent", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # content
    op.create_table(
        "content",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("webapp_id", sa.String(length=255), sa.ForeignKey("webapps.id"), nullable=False),
        sa.Column("platform", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("caption", sa.String(length=255), nullable=False),
        sa.Column("hashtags", sa.JSON(), nullable=True),
        sa.Column("media_urls", sa.JSON(), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("platform_post_id", sa.String(length=255), nullable=True),
        sa.Column("content_angle", sa.String(length=255), nullable=True),
        sa.Column("target_audience", sa.String(length=255), nullable=True),
        sa.Column("language", sa.String(length=255), nullable=True),
        sa.Column("viral_score", sa.Integer(), nullable=True),
        sa.Column("confidence_score", sa.Integer(), nullable=True),
        sa.Column("views", sa.Integer(), nullable=True),
        sa.Column("likes", sa.Integer(), nullable=True),
        sa.Column("comments", sa.Integer(), nullable=True),
        sa.Column("shares", sa.Integer(), nullable=True),
        sa.Column("clicks", sa.Integer(), nullable=True),
        sa.Column("ctr", sa.Float(), nullable=True),
        sa.Column("is_variant", sa.Boolean(), nullable=True),
        sa.Column("ab_test_id", sa.String(length=255), sa.ForeignKey("ab_tests.id"), nullable=True),
        sa.Column("variant_id", sa.String(length=255), nullable=True),
        sa.Column("image_generation_cost", sa.String(length=255), nullable=True),
        sa.Column("video_generation_cost", sa.String(length=255), nullable=True),
        sa.Column("audio_generation_cost", sa.String(length=255), nullable=True),
        sa.Column("llm_tokens_used", sa.Integer(), nullable=True),
        sa.Column("parent_content_id", sa.String(length=255), sa.ForeignKey("content.id"), nullable=True),
        sa.Column("is_repurposed", sa.Boolean(), nullable=True),
        sa.Column("repurposed_for_platforms", sa.JSON(), nullable=True),
        sa.Column("performance_feedback", sa.JSON(), nullable=True),
        sa.Column("generation_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_content_id", "content", ["id"], unique=False)

    # analytics
    op.create_table(
        "analytics",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("platform", sa.String(length=255), nullable=True),
        sa.Column("date", sa.String(length=255), nullable=True),
        sa.Column("views", sa.Integer(), nullable=True),
        sa.Column("engagements", sa.Integer(), nullable=True),
        sa.Column("leads_generated", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # user_api_keys
    op.create_table(
        "user_api_keys",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("key_name", sa.String(length=255), nullable=False),
        sa.Column("encrypted_key", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("usage_count", sa.String(length=255), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_api_keys_id", "user_api_keys", ["id"], unique=False)
    op.create_index("ix_user_api_keys_user_id", "user_api_keys", ["user_id"], unique=False)

    # user_integrations
    op.create_table(
        "user_integrations",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("platform", sa.String(length=255), nullable=False),
        sa.Column("encrypted_access_token", sa.Text(), nullable=True),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_connected", sa.Boolean(), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disconnected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("platform_user_id", sa.String(length=255), nullable=True),
        sa.Column("platform_username", sa.String(length=255), nullable=True),
        sa.Column("platform_data", sa.Text(), nullable=True),
        sa.Column("scopes", sa.Text(), nullable=True),
        sa.Column("auto_post_enabled", sa.Boolean(), nullable=True),
        sa.Column("auto_reply_enabled", sa.Boolean(), nullable=True),
        sa.Column("low_risk_auto_reply", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_integrations_id", "user_integrations", ["id"], unique=False)
    op.create_index("ix_user_integrations_user_id", "user_integrations", ["user_id"], unique=False)

    # engagement_replies
    op.create_table(
        "engagement_replies",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("platform", sa.String(length=255), nullable=False),
        sa.Column("engagement_type", sa.String(length=255), nullable=True),
        sa.Column("platform_comment_id", sa.String(length=255), nullable=True),
        sa.Column("platform_post_id", sa.String(length=255), nullable=True),
        sa.Column("author_name", sa.String(length=255), nullable=True),
        sa.Column("author_platform_id", sa.String(length=255), nullable=True),
        sa.Column("original_text", sa.Text(), nullable=True),
        sa.Column("ai_reply_text", sa.Text(), nullable=True),
        sa.Column("ai_reply_confidence", sa.Float(), nullable=True),
        sa.Column("final_reply_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=255), nullable=True),
        sa.Column("priority", sa.String(length=255), nullable=True),
        sa.Column("auto_reply_safe", sa.Boolean(), nullable=True),
        sa.Column("sentiment", sa.String(length=255), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # viral_scores
    op.create_table(
        "viral_scores",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("content_id", sa.String(length=255), sa.ForeignKey("content.id"), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("factors", sa.JSON(), nullable=True),
        sa.Column("predicted_views", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # cost_tracking
    op.create_table(
        "cost_tracking",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("date", sa.String(length=255), nullable=True),
        sa.Column("service", sa.String(length=255), nullable=True),
        sa.Column("cost", sa.String(length=255), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("cost_tracking")
    op.drop_table("viral_scores")
    op.drop_table("engagement_replies")
    op.drop_table("user_integrations")
    op.drop_table("user_api_keys")
    op.drop_table("analytics")
    op.drop_table("content")
    op.drop_table("ab_tests")
    op.drop_table("platform_connections")
    op.drop_table("webapps")
    op.drop_table("users")
