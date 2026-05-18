from sqlalchemy import Column, String, DateTime, Enum, Integer, Float, Boolean, JSON, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum

class PlanType(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # nullable for social-auth compat
    name = Column(String(255), nullable=True)
    avatar = Column(String(512), nullable=True)
    plan = Column(Enum(PlanType), default=PlanType.FREE)
    
    # Usage limits and tracking
    monthly_content_quota = Column(Integer, default=10)  # Posts per month
    monthly_content_used = Column(Integer, default=0)
    api_cost_budget = Column(String(20), default="5.00")  # Monthly AI generation budget
    api_cost_used = Column(String(20), default="0.00")
    
    # Feature flags
    auto_post_enabled = Column(Boolean, default=False)
    auto_reply_enabled = Column(Boolean, default=False)
    low_risk_auto_reply = Column(Boolean, default=False)
    
    # Preferences
    preferred_language = Column(String(10), default="en")
    timezone = Column(String(64), default="UTC")
    notification_preferences = Column(JSON, default=dict)

    # Phase 2: extended plan/quota tracking
    plan_tier = Column(String(32), default="free")
    plan_quota_content = Column(Integer, default=50)
    plan_quota_used = Column(Integer, default=0)
    notification_email = Column(Boolean, default=True)
    notification_digest = Column(Boolean, default=True)
    settings_json = Column(Text, nullable=True)  # arbitrary JSON prefs

    # Email verification & billing
    email_verified = Column(Boolean, default=False)

    # Referral program
    referral_code = Column(String(16), unique=True, nullable=True, index=True)
    referred_by = Column(String(36), ForeignKey("users.id"), nullable=True)

    # Geolocation (captured via browser Geolocation API on login)
    geo_lat = Column(Float, nullable=True)
    geo_lon = Column(Float, nullable=True)

    # Stripe billing
    stripe_customer_id = Column(String(255), nullable=True, unique=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    webapps = relationship("WebApp", back_populates="user", cascade="all, delete-orphan")
    platform_connections = relationship("PlatformConnection", back_populates="user", cascade="all, delete-orphan")
    content = relationship("Content", back_populates="user", cascade="all, delete-orphan")
    analytics = relationship("Analytics", back_populates="user", cascade="all, delete-orphan")
    
    # New relationships
    api_keys = relationship("UserAPIKey", back_populates="user", cascade="all, delete-orphan")
    integrations = relationship("UserIntegration", back_populates="user", cascade="all, delete-orphan")
    engagement_replies = relationship(
        "EngagementReply",
        primaryjoin="EngagementReply.user_id == User.id",
        foreign_keys="[EngagementReply.user_id]",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    ab_tests = relationship("ABTest", back_populates="user", cascade="all, delete-orphan")
    viral_scores = relationship("ViralScore", back_populates="user", cascade="all, delete-orphan")
    cost_tracking = relationship("CostTracking", back_populates="user", cascade="all, delete-orphan")
