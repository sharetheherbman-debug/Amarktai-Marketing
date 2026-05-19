"""Add all 10 power tool tables

Revision ID: 0002_power_tools
Revises: 0001_initial
Create Date: 2026-02-24
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002_power_tools"
down_revision: Union[str, None] = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. content_remixes
    op.create_table(
        "content_remixes",
        sa.Column("id", sa.String(length=255), primary_key=True, index=True),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("webapp_id", sa.String(length=255), sa.ForeignKey("webapps.id"), nullable=True),
        sa.Column("source_type", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.String(length=255), nullable=True),
        sa.Column("source_text", sa.Text(), nullable=True),
        sa.Column("source_title", sa.String(length=255), nullable=True),
        sa.Column("target_platforms", sa.JSON(), nullable=True),
        sa.Column("snippets", sa.JSON(), nullable=True),
        sa.Column("trending_hashtags", sa.JSON(), nullable=True),
        sa.Column("auto_schedule", sa.Boolean(), nullable=True),
        sa.Column("remix_booster_enabled", sa.Boolean(), nullable=True),
        sa.Column("status", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 2. competitor_profiles
    op.create_table(
        "competitor_profiles",
        sa.Column("id", sa.String(length=255), primary_key=True, index=True),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("competitor_name", sa.String(length=255), nullable=False),
        sa.Column("competitor_url", sa.String(length=255), nullable=False),
        sa.Column("social_handles", sa.JSON(), nullable=True),
        sa.Column("our_niche", sa.String(length=255), nullable=True),
        sa.Column("last_scraped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scraped_content_preview", sa.Text(), nullable=True),
        sa.Column("content_strategy", sa.Text(), nullable=True),
        sa.Column("strengths", sa.JSON(), nullable=True),
        sa.Column("weaknesses", sa.JSON(), nullable=True),
        sa.Column("content_gaps", sa.JSON(), nullable=True),
        sa.Column("counter_strategies", sa.JSON(), nullable=True),
        sa.Column("top_topics", sa.JSON(), nullable=True),
        sa.Column("posting_frequency", sa.String(length=255), nullable=True),
        sa.Column("engagement_level", sa.String(length=255), nullable=True),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column("predicted_next_moves", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 3. feedback_analyses
    op.create_table(
        "feedback_analyses",
        sa.Column("id", sa.String(length=255), primary_key=True, index=True),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("webapp_id", sa.String(length=255), sa.ForeignKey("webapps.id"), nullable=True),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column("raw_feedback", sa.JSON(), nullable=True),
        sa.Column("overall_sentiment", sa.String(length=255), nullable=True),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column("key_themes", sa.JSON(), nullable=True),
        sa.Column("praise_points", sa.JSON(), nullable=True),
        sa.Column("pain_points", sa.JSON(), nullable=True),
        sa.Column("ad_copy_suggestions", sa.JSON(), nullable=True),
        sa.Column("response_templates", sa.JSON(), nullable=True),
        sa.Column("ab_test_ideas", sa.JSON(), nullable=True),
        sa.Column("auto_apply_to_templates", sa.Boolean(), nullable=True),
        sa.Column("status", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 4. echo_amplifications
    op.create_table(
        "echo_amplifications",
        sa.Column("id", sa.String(length=255), primary_key=True, index=True),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("trigger_text", sa.Text(), nullable=False),
        sa.Column("trigger_source", sa.String(length=255), nullable=True),
        sa.Column("brand_voice", sa.String(length=255), nullable=True),
        sa.Column("thread_posts", sa.JSON(), nullable=True),
        sa.Column("story_content", sa.JSON(), nullable=True),
        sa.Column("virality_score", sa.Float(), nullable=True),
        sa.Column("priority", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 5. seo_mirage_reports
    op.create_table(
        "seo_mirage_reports",
        sa.Column("id", sa.String(length=255), primary_key=True, index=True),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("content_id", sa.String(length=255), sa.ForeignKey("content.id"), nullable=True),
        sa.Column("target_url", sa.String(length=255), nullable=True),
        sa.Column("input_text", sa.Text(), nullable=True),
        sa.Column("platform", sa.String(length=255), nullable=True),
        sa.Column("seo_title", sa.String(length=255), nullable=True),
        sa.Column("seo_description", sa.String(length=255), nullable=True),
        sa.Column("alt_text", sa.String(length=255), nullable=True),
        sa.Column("optimized_hashtags", sa.JSON(), nullable=True),
        sa.Column("keyword_density_report", sa.JSON(), nullable=True),
        sa.Column("algorithm_tips", sa.JSON(), nullable=True),
        sa.Column("enhanced_caption", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )

    # 6. churn_shield_reports
    op.create_table(
        "churn_shield_reports",
        sa.Column("id", sa.String(length=255), primary_key=True, index=True),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("platform", sa.String(length=255), nullable=False),
        sa.Column("analysis_date", sa.String(length=255), nullable=True),
        sa.Column("churn_risk_score", sa.Float(), nullable=True),
        sa.Column("at_risk_segments", sa.JSON(), nullable=True),
        sa.Column("dropout_patterns", sa.JSON(), nullable=True),
        sa.Column("reengagement_posts", sa.JSON(), nullable=True),
        sa.Column("dm_templates", sa.JSON(), nullable=True),
        sa.Column("loyalty_campaign", sa.JSON(), nullable=True),
        sa.Column("auto_deploy", sa.Boolean(), nullable=True),
        sa.Column("status", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )

    # 7. harmony_pricer_reports
    op.create_table(
        "harmony_pricer_reports",
        sa.Column("id", sa.String(length=255), primary_key=True, index=True),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("current_price", sa.String(length=255), nullable=True),
        sa.Column("platform", sa.String(length=255), nullable=True),
        sa.Column("competitor_prices", sa.JSON(), nullable=True),
        sa.Column("buzz_score", sa.Float(), nullable=True),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column("recommended_price", sa.String(length=255), nullable=True),
        sa.Column("price_rationale", sa.Text(), nullable=True),
        sa.Column("ad_copy_variants", sa.JSON(), nullable=True),
        sa.Column("simulated_roi", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )

    # 8. viral_spark_reports
    op.create_table(
        "viral_spark_reports",
        sa.Column("id", sa.String(length=255), primary_key=True, index=True),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("webapp_id", sa.String(length=255), sa.ForeignKey("webapps.id"), nullable=True),
        sa.Column("report_date", sa.String(length=255), nullable=True),
        sa.Column("niche", sa.String(length=255), nullable=True),
        sa.Column("trending_topics", sa.JSON(), nullable=True),
        sa.Column("viral_opportunities", sa.JSON(), nullable=True),
        sa.Column("hooks", sa.JSON(), nullable=True),
        sa.Column("challenges", sa.JSON(), nullable=True),
        sa.Column("best_posting_windows", sa.JSON(), nullable=True),
        sa.Column("predicted_reach_multiplier", sa.Float(), nullable=True),
        sa.Column("auto_inject_hooks", sa.Boolean(), nullable=True),
        sa.Column("status", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )

    # 9. audience_map_reports
    op.create_table(
        "audience_map_reports",
        sa.Column("id", sa.String(length=255), primary_key=True, index=True),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("webapp_id", sa.String(length=255), sa.ForeignKey("webapps.id"), nullable=True),
        sa.Column("platform", sa.String(length=255), nullable=True),
        sa.Column("data_summary", sa.Text(), nullable=True),
        sa.Column("segments", sa.JSON(), nullable=True),
        sa.Column("campaign_suggestions", sa.JSON(), nullable=True),
        sa.Column("targeting_recommendations", sa.JSON(), nullable=True),
        sa.Column("cross_platform_insights", sa.JSON(), nullable=True),
        sa.Column("response_mirage", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )

    # 10. ad_alchemy_reports
    op.create_table(
        "ad_alchemy_reports",
        sa.Column("id", sa.String(length=255), primary_key=True, index=True),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("content_id", sa.String(length=255), sa.ForeignKey("content.id"), nullable=True),
        sa.Column("product_or_service", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=255), nullable=True),
        sa.Column("current_copy", sa.Text(), nullable=True),
        sa.Column("variants", sa.JSON(), nullable=True),
        sa.Column("recommended_winner", sa.JSON(), nullable=True),
        sa.Column("global_benchmark_comparison", sa.JSON(), nullable=True),
        sa.Column("improvement_suggestions", sa.JSON(), nullable=True),
        sa.Column("auto_deploy_winner", sa.Boolean(), nullable=True),
        sa.Column("status", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("ad_alchemy_reports")
    op.drop_table("audience_map_reports")
    op.drop_table("viral_spark_reports")
    op.drop_table("harmony_pricer_reports")
    op.drop_table("churn_shield_reports")
    op.drop_table("seo_mirage_reports")
    op.drop_table("echo_amplifications")
    op.drop_table("feedback_analyses")
    op.drop_table("competitor_profiles")
    op.drop_table("content_remixes")
