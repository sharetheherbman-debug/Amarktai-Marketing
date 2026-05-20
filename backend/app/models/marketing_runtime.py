from __future__ import annotations

import enum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.sql import func

from app.db.base import Base


class SchedulerStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    POSTED = "posted"
    FAILED = "failed"
    MANUAL_REVIEW = "manual_review"


class SchedulerMode(str, enum.Enum):
    MANUAL = "manual"
    AUTO = "auto"


class SchedulerItem(Base):
    __tablename__ = "scheduler_items"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    business_id = Column(String(36), ForeignKey("webapps.id"), nullable=False, index=True)
    content_id = Column(String(36), ForeignKey("content.id"), nullable=False, index=True)
    platform = Column(String(64), nullable=False, index=True)
    title = Column(String(512), nullable=False, default="")
    planned_at = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(String(32), nullable=False, default=SchedulerStatus.SCHEDULED.value, index=True)
    posting_readiness = Column(String(32), nullable=False, default="planning_only")
    mode = Column(String(16), nullable=False, default=SchedulerMode.MANUAL.value)
    notes = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class MediaJobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PROMPT_ONLY = "prompt_only"


class MediaJob(Base):
    __tablename__ = "media_jobs"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    business_id = Column(String(36), ForeignKey("webapps.id"), nullable=False, index=True)
    content_id = Column(String(36), ForeignKey("content.id"), nullable=True, index=True)
    provider = Column(String(64), nullable=False, default="template")
    model = Column(String(128), nullable=True)
    task = Column(String(64), nullable=False, default="media_generation")
    external_job_id = Column(String(255), nullable=True, index=True)
    status = Column(String(32), nullable=False, default=MediaJobStatus.QUEUED.value, index=True)
    prompt = Column(Text, nullable=True)
    result_url = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    business_id = Column(String(36), ForeignKey("webapps.id"), nullable=False, index=True)
    content_id = Column(String(36), ForeignKey("content.id"), nullable=True, index=True)
    media_job_id = Column(String(36), ForeignKey("media_jobs.id"), nullable=True, index=True)
    provider = Column(String(64), nullable=False, default="template")
    model = Column(String(128), nullable=True)
    asset_type = Column(String(32), nullable=False, default="prompt")
    title = Column(String(255), nullable=False, default="")
    url = Column(Text, nullable=True)
    preview_url = Column(Text, nullable=True)
    prompt = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LearningRun(Base):
    __tablename__ = "learning_runs"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    business_id = Column(String(36), ForeignKey("webapps.id"), nullable=True, index=True)
    status = Column(String(32), nullable=False, default="completed")
    metrics_records = Column(Integer, nullable=False, default=0)
    generated_count = Column(Integer, nullable=False, default=0)
    summary = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class LearningInsight(Base):
    __tablename__ = "learning_insights"

    id = Column(String(36), primary_key=True, index=True)
    learning_run_id = Column(String(36), ForeignKey("learning_runs.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    business_id = Column(String(36), ForeignKey("webapps.id"), nullable=True, index=True)
    platform = Column(String(64), nullable=True, index=True)
    format = Column(String(64), nullable=True)
    provider = Column(String(64), nullable=True)
    model = Column(String(128), nullable=True)
    what_worked = Column(JSON, nullable=True, default=list)
    what_failed = Column(JSON, nullable=True, default=list)
    recommendations = Column(JSON, nullable=True, default=list)
    metadata_json = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class BusinessPlatformPreference(Base):
    __tablename__ = "business_platform_preferences"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    business_id = Column(String(36), ForeignKey("webapps.id"), nullable=False, index=True)
    platform = Column(String(64), nullable=False, index=True)
    preferred_provider = Column(String(64), nullable=True)
    preferred_model = Column(String(128), nullable=True)
    budget_mode = Column(String(32), nullable=True)
    preferred_formats = Column(JSON, nullable=True, default=list)
    metadata_json = Column(JSON, nullable=True, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
