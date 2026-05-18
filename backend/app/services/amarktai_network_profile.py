"""
AmarktAI Network — App Registration Profile
=============================================

Canonical registration data, capability pack, and gap analysis for
AmarktAI Marketing.  Used by:
  - /api/amarktai/status (enriched response)
  - AmarktAI Network super brain for routing decisions
  - Admin lab for testability

This file is the single source of truth for this app's identity
and capabilities within the AmarktAI Network.
"""

from __future__ import annotations

from app.core.config import settings

# ─── App Identity ─────────────────────────────────────────────────────────────

APP_PROFILE = {
    "app_name": "AmarktAI Marketing",
    "slug": "amarktai-marketing",
    "app_id": "amarktai-marketing",
    "version": settings.APP_VERSION,
    "category": "marketing",
    "description": (
        "AI-powered autonomous social media marketing platform. "
        "Generates, schedules, posts, and analyses content across 12+ platforms "
        "using multi-provider LLM abstraction and real platform APIs."
    ),

    # ── Hosting & environment truth ────────────────────────────────────────
    "hosting_scope": "subdomain",
    "subdomain": "marketing.amarktai.com",
    "environment": settings.APP_ENVIRONMENT,  # production | staging | development
    "access_model": "public",  # public signup, no invite required
    "ai_required": True,
    "monitoring_required": True,
    "integrations_required": True,

    # ── Onboarding / connection status ─────────────────────────────────────
    # These must be checked dynamically — see get_connection_state() below.
}


# ─── Capability Pack ──────────────────────────────────────────────────────────
#
# The canonical set of AI capabilities this marketing app needs.
# Each entry is:
#   capability_id:  { needed: bool, status: str, notes: str }
#
# status values:
#   "active"          — fully wired and working with current keys
#   "available"       — supported by brain, needs key/config to activate
#   "not_wired"       — brain supports it but this app hasn't integrated it yet
#   "not_supported"   — brain does not support this capability yet
#   "not_needed"      — this app does not require this capability

CAPABILITY_PACK = {
    "chat": {
        "needed": False,
        "status": "not_needed",
        "notes": "Marketing app generates content, does not provide interactive chat.",
    },
    "reasoning": {
        "needed": True,
        "status": "active",
        "notes": "Used for content generation, sentiment analysis, keyword extraction. Multi-provider chain: AmarktAI Network → Qwen → HuggingFace → OpenAI → Gemini → template.",
    },
    "retrieval": {
        "needed": False,
        "status": "not_needed",
        "notes": "No RAG / document retrieval required for content generation.",
    },
    "embeddings": {
        "needed": False,
        "status": "not_needed",
        "notes": "Content similarity is handled by engagement heuristics, not vector search.",
    },
    "reranking": {
        "needed": False,
        "status": "not_needed",
        "notes": "No reranking pipeline in the content workflow.",
    },
    "image_generation": {
        "needed": True,
        "status": "active",
        "notes": "HuggingFace FLUX.1-schnell / SDXL with picsum placeholder fallback. Wired into content generation.",
    },
    "image_editing": {
        "needed": False,
        "status": "not_needed",
        "notes": "Generated images are used as-is; no editing pipeline.",
    },
    "video_generation": {
        "needed": True,
        "status": "active",
        "notes": "HuggingFace text-to-video with stock video fallback. Used for YouTube/TikTok/Reels.",
    },
    "moderation": {
        "needed": True,
        "status": "available",
        "notes": "Engagement AI includes sentiment/risk analysis. Brain-level moderation available when integrated.",
    },
    "scraping": {
        "needed": True,
        "status": "active",
        "notes": "Webapp URL scraping for content enrichment. Uses BeautifulSoup + httpx.",
    },
    "app_analysis": {
        "needed": True,
        "status": "active",
        "notes": "Competitor analysis, viral prediction, churn check, SEO, audience mapping — all implemented as daily tasks.",
    },
    "agents": {
        "needed": True,
        "status": "active",
        "notes": "CommunityAgent for engagement reply generation. ContentAgent for autonomous posting.",
    },
    "voice": {
        "needed": False,
        "status": "not_needed",
        "notes": "No voice capability required for social media content.",
    },
    "video_understanding": {
        "needed": False,
        "status": "not_needed",
        "notes": "Content is generated, not analysed from video input.",
    },
    "adult": {
        "needed": False,
        "status": "not_needed",
        "notes": "Adult content generation is OFF. This is a professional marketing tool.",
    },
}


# ─── Provider / Model Strategy ───────────────────────────────────────────────

def get_provider_readiness() -> dict:
    """Return current provider availability for this app."""
    providers = []

    # AmarktAI Network (top priority when configured)
    amarktai_ready = bool(
        settings.AMARKTAI_INTEGRATION_ENABLED
        and settings.AMARKTAI_DASHBOARD_URL
        and settings.AMARKTAI_INTEGRATION_TOKEN
    )
    providers.append({
        "provider": "amarktai_network",
        "role": "primary_router",
        "ready": amarktai_ready,
        "capabilities": ["reasoning", "moderation"],
        "cost_tier": "included",
        "notes": "Top-priority brain routing" if amarktai_ready else "Set AMARKTAI_INTEGRATION_TOKEN + AMARKTAI_DASHBOARD_URL to activate",
    })

    providers.append({
        "provider": "genx",
        "role": "primary_local",
        "ready": bool(settings.GENX_API_KEY),
        "capabilities": ["reasoning", "analysis", "long_form", "moderation"],
        "cost_tier": "variable",
        "notes": "GenX unified provider with multi-model routing",
    })
    providers.append({
        "provider": "qwen",
        "role": "secondary_fallback",
        "ready": bool(settings.QWEN_API_KEY),
        "capabilities": ["reasoning"],
        "cost_tier": "low",
        "notes": "Alibaba DashScope — lowest cost LLM",
    })
    providers.append({
        "provider": "huggingface",
        "role": "fallback",
        "ready": bool(settings.HUGGINGFACE_TOKEN),
        "capabilities": ["reasoning", "image_generation", "video_generation"],
        "cost_tier": "free",
        "notes": "HF Inference API — free tier with model fallbacks",
    })
    providers.append({
        "provider": "openai",
        "role": "premium_fallback",
        "ready": bool(settings.OPENAI_API_KEY),
        "capabilities": ["reasoning"],
        "cost_tier": "premium",
        "notes": "GPT-3.5-turbo — higher quality, higher cost",
    })
    providers.append({
        "provider": "gemini",
        "role": "optional",
        "ready": bool(settings.GEMINI_API_KEY or settings.GOOGLE_GEMINI_API_KEY),
        "capabilities": ["reasoning"],
        "cost_tier": "free",
        "notes": "Google Gemini Pro — optional free tier",
    })
    providers.append({
        "provider": "template",
        "role": "guaranteed_fallback",
        "ready": True,
        "capabilities": ["reasoning"],
        "cost_tier": "free",
        "notes": "Template-based content generation — always available",
    })

    return {
        "providers": providers,
        "any_ai_ready": any(p["ready"] for p in providers if p["provider"] != "template"),
        "primary_provider": next(
            (p["provider"] for p in providers if p["ready"] and p["provider"] != "template"),
            "template",
        ),
    }


# ─── Gap Analysis ─────────────────────────────────────────────────────────────

def get_capability_gaps() -> list[dict]:
    """
    Return a list of capability gaps.
    Each entry:
      { capability, classification, detail }

    classification:
      1 = already supported by brain, just needs wiring
      2 = supportable once keys/config are added
      3 = not yet implemented in the brain
    """
    gaps = []

    # Check if brain routing is active
    if not (settings.AMARKTAI_INTEGRATION_ENABLED and settings.AMARKTAI_INTEGRATION_TOKEN):
        gaps.append({
            "capability": "brain_routing",
            "classification": 2,
            "detail": "AmarktAI Network brain routing not active. Set AMARKTAI_INTEGRATION_ENABLED=true, AMARKTAI_DASHBOARD_URL, AMARKTAI_INTEGRATION_TOKEN.",
        })

    # Check Stripe billing
    if not settings.STRIPE_SECRET_KEY:
        gaps.append({
            "capability": "billing",
            "classification": 2,
            "detail": "Stripe billing not configured. Set STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, and plan price IDs.",
        })

    # Check email
    if not settings.RESEND_API_KEY:
        gaps.append({
            "capability": "email_workflows",
            "classification": 2,
            "detail": "Email service (Resend) not configured. Set RESEND_API_KEY.",
        })

    # Check platform OAuth keys
    platform_gaps = []
    if not settings.META_APP_ID:
        platform_gaps.append("Meta (FB/IG)")
    if not settings.YOUTUBE_CLIENT_ID:
        platform_gaps.append("YouTube")
    if not settings.TWITTER_CLIENT_ID:
        platform_gaps.append("Twitter/X")
    if not settings.LINKEDIN_CLIENT_ID:
        platform_gaps.append("LinkedIn")
    if not settings.TIKTOK_CLIENT_KEY:
        platform_gaps.append("TikTok")
    if platform_gaps:
        gaps.append({
            "capability": "platform_oauth",
            "classification": 2,
            "detail": f"OAuth credentials missing for: {', '.join(platform_gaps)}. Users cannot connect these platforms until keys are set.",
        })

    # Check AI providers
    if not (settings.GENX_API_KEY or settings.QWEN_API_KEY or settings.HUGGINGFACE_TOKEN or settings.OPENAI_API_KEY):
        gaps.append({
            "capability": "ai_generation",
            "classification": 2,
            "detail": "No AI provider keys configured. Content will use template fallback only.",
        })

    return gaps


# ─── Connection State ─────────────────────────────────────────────────────────

def get_connection_state() -> dict:
    """Return the truthful integration/connection state for this app."""
    integration_enabled = bool(
        settings.AMARKTAI_INTEGRATION_ENABLED
        and settings.AMARKTAI_DASHBOARD_URL
        and settings.AMARKTAI_INTEGRATION_TOKEN
    )
    ai_ready = bool(settings.GENX_API_KEY or settings.QWEN_API_KEY or settings.HUGGINGFACE_TOKEN or settings.OPENAI_API_KEY)
    billing_ready = bool(settings.STRIPE_SECRET_KEY)
    email_ready = bool(settings.RESEND_API_KEY)

    gaps = get_capability_gaps()
    provider_readiness = get_provider_readiness()

    # Determine readiness
    if integration_enabled and ai_ready:
        readiness = "READY_TO_CONNECT"
    elif ai_ready:
        readiness = "READY_FOR_INTERNAL_TESTING"
    else:
        readiness = "NOT_READY"

    return {
        "connected_to_brain": integration_enabled,
        "ai_enabled": ai_ready,
        "billing_enabled": billing_ready,
        "email_enabled": email_ready,
        "ready_to_deploy": integration_enabled and ai_ready,
        "readiness": readiness,
        "capability_gaps": gaps,
        "provider_readiness": provider_readiness,
        "adult_content": False,  # Always OFF for this app
        "moderation_enabled": True,
    }
