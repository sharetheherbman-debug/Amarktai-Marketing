from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth, users, webapps, platforms, content, analytics, analytics_export,
    integrations, engagement, ab_testing, cost_tracking, autonomous, admin,
    remix, tools, leads, groups, blog, oauth, billing, events,
    amarktai_status, dashboard, settings, contact,
    stats, changelog, notifications, scheduler, publishing, social_rules,
)

api_router = APIRouter()

# Core routes
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(webapps.router, prefix="/webapps", tags=["webapps"])
api_router.include_router(platforms.router, prefix="/platforms", tags=["platforms"])
api_router.include_router(content.router, prefix="/content", tags=["content"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(analytics_export.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(leads.router, prefix="/leads", tags=["leads"])
api_router.include_router(groups.router, prefix="/groups", tags=["groups"])

# Phase 2 & 3 routes
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
api_router.include_router(engagement.router, prefix="/engagement", tags=["engagement"])
api_router.include_router(ab_testing.router, prefix="/ab-testing", tags=["ab-testing"])
api_router.include_router(cost_tracking.router, prefix="/cost-tracking", tags=["cost-tracking"])
api_router.include_router(autonomous.router, prefix="/autonomous", tags=["autonomous"])

# Admin
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])

# Power Tools (all 10 add-ons)
api_router.include_router(remix.router, prefix="/remix", tags=["tools"])
api_router.include_router(tools.router, prefix="/tools", tags=["tools"])

# SEO Blog Generator
# Blog (SEO blog post generator)
api_router.include_router(blog.router, prefix="/blog", tags=["blog"])

# Dashboard feature endpoints (insights, scheduler, predictions, calendar, competitors)
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])

# AmarktAI Network integration status (public, no auth)
# Accessible at /api/v1/amarktai/status  AND  /api/amarktai/status (via main.py mount)
api_router.include_router(amarktai_status.router, prefix="/amarktai", tags=["integration"])

# Settings & preferences (user API keys, billing, notifications)
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(scheduler.router, prefix="/scheduler", tags=["scheduler"])
api_router.include_router(publishing.router, prefix="/publishing", tags=["publishing"])
api_router.include_router(social_rules.router, prefix="/social-rules", tags=["social-rules"])

# Stripe billing (checkout, webhook, portal)
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])

# Contact form (public, no auth, rate limited)
api_router.include_router(contact.router, prefix="/contact", tags=["contact"])

# OAuth2 flows for social platform connections
api_router.include_router(oauth.router, prefix="/oauth", tags=["oauth"])

# Real-time SSE events
api_router.include_router(events.router, prefix="/events", tags=["events"])
# Public stats (no auth)
api_router.include_router(stats.router, prefix="/stats", tags=["stats"])

# Public changelog (no auth)
api_router.include_router(changelog.router, prefix="/changelog", tags=["changelog"])

# Notifications (auth required)
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
