"""Add leads table and new social platforms

Revision ID: 0003
Revises: 0002
Create Date: 2026-02-24
"""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002_power_tools'
branch_labels = None
depends_on = None


def upgrade():
    # Create leads table
    op.create_table(
        'leads',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=255), nullable=True),
        sa.Column('company', sa.String(length=255), nullable=True),
        sa.Column('source_platform', sa.String(length=255), nullable=True),
        sa.Column('source_content_id', sa.String(length=255), nullable=True),
        sa.Column('source_webapp_id', sa.String(length=255), nullable=True),
        sa.Column('utm_source', sa.String(length=255), nullable=True),
        sa.Column('utm_medium', sa.String(length=255), nullable=True),
        sa.Column('utm_campaign', sa.String(length=255), nullable=True),
        sa.Column('utm_content', sa.String(length=255), nullable=True),
        sa.Column('utm_term', sa.String(length=255), nullable=True),
        sa.Column('qualifiers', sa.JSON(), nullable=True),
        sa.Column('lead_score', sa.Integer(), nullable=True),
        sa.Column('is_qualified', sa.Boolean(), nullable=True),
        sa.Column('qualification_notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('converted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('conversion_value', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_content_id'], ['content.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_webapp_id'], ['webapps.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_leads_id', 'leads', ['id'])
    op.create_index('ix_leads_user_id', 'leads', ['user_id'])
    op.create_index('ix_leads_email', 'leads', ['email'])

    # Extend platform enum when present (older schemas may use plain VARCHAR)
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'platformtype') THEN
                ALTER TYPE platformtype ADD VALUE IF NOT EXISTS 'pinterest';
                ALTER TYPE platformtype ADD VALUE IF NOT EXISTS 'reddit';
                ALTER TYPE platformtype ADD VALUE IF NOT EXISTS 'bluesky';
                ALTER TYPE platformtype ADD VALUE IF NOT EXISTS 'threads';
                ALTER TYPE platformtype ADD VALUE IF NOT EXISTS 'telegram';
                ALTER TYPE platformtype ADD VALUE IF NOT EXISTS 'snapchat';
            END IF;
        END$$;
        """
    )


def downgrade():
    op.drop_index('ix_leads_email', 'leads')
    op.drop_index('ix_leads_user_id', 'leads')
    op.drop_index('ix_leads_id', 'leads')
    op.drop_table('leads')
    # Note: PostgreSQL does not support removing enum values; downgrade skips enum changes
