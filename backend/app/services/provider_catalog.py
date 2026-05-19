from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.user_api_key import UserAPIKey

USER_PROVIDER_KEYS: list[dict[str, Any]] = [
    {
        "key_name": "GENX_API_KEY",
        "label": "GenX API Key",
        "provider": "GenX",
        "required": True,
        "description": "Required for live AI generation.",
    },
    {
        "key_name": "FIRECRAWL_API_KEY",
        "label": "Firecrawl API Key",
        "provider": "Firecrawl",
        "required": True,
        "description": "Required for live scraping and research.",
    },
    {
        "key_name": "QWEN_API_KEY",
        "label": "Qwen API Key",
        "provider": "Qwen",
        "required": False,
        "description": "Optional fallback provider.",
    },
    {
        "key_name": "HUGGINGFACE_TOKEN",
        "label": "HuggingFace Token",
        "provider": "HuggingFace",
        "required": False,
        "description": "Optional fallback provider.",
    },
    {
        "key_name": "OPENAI_API_KEY",
        "label": "OpenAI API Key",
        "provider": "OpenAI",
        "required": False,
        "description": "Optional fallback provider.",
    },
    {
        "key_name": "GEMINI_API_KEY",
        "label": "Gemini API Key",
        "provider": "Gemini",
        "required": False,
        "description": "Optional fallback provider.",
    },
]

USER_PROVIDER_KEY_NAMES = {item["key_name"] for item in USER_PROVIDER_KEYS}

GLOBAL_ENV_KEYS: list[dict[str, Any]] = [
    {
        "key_name": "GENX_API_KEY",
        "label": "Global GenX API Key",
        "group": "Global provider fallback",
        "required": False,
        "secret": True,
    },
    {
        "key_name": "FIRECRAWL_API_KEY",
        "label": "Global Firecrawl API Key",
        "group": "Global provider fallback",
        "required": False,
        "secret": True,
    },
    {
        "key_name": "QWEN_API_KEY",
        "label": "Global Qwen API Key",
        "group": "Global provider fallback",
        "required": False,
        "secret": True,
    },
    {
        "key_name": "HUGGINGFACE_TOKEN",
        "label": "Global HuggingFace Token",
        "group": "Global provider fallback",
        "required": False,
        "secret": True,
    },
    {
        "key_name": "OPENAI_API_KEY",
        "label": "Global OpenAI API Key",
        "group": "Global provider fallback",
        "required": False,
        "secret": True,
    },
    {
        "key_name": "GEMINI_API_KEY",
        "label": "Global Gemini API Key",
        "group": "Global provider fallback",
        "required": False,
        "secret": True,
    },
    {
        "key_name": "GENX_BASE_URL",
        "label": "GenX Base URL",
        "group": "GenX runtime",
        "required": True,
        "secret": False,
    },
    {
        "key_name": "GENX_DEFAULT_MODEL",
        "label": "GenX Default Model",
        "group": "GenX runtime",
        "required": True,
        "secret": False,
    },
    {
        "key_name": "GENX_MODEL_COPY",
        "label": "GenX Copy Model Override",
        "group": "GenX runtime",
        "required": False,
        "secret": False,
    },
    {
        "key_name": "GENX_MODEL_STRATEGY",
        "label": "GenX Strategy Model Override",
        "group": "GenX runtime",
        "required": False,
        "secret": False,
    },
    {
        "key_name": "GENX_MODEL_ANALYSIS",
        "label": "GenX Analysis Model Override",
        "group": "GenX runtime",
        "required": False,
        "secret": False,
    },
    {
        "key_name": "GENX_MODEL_LONG_FORM",
        "label": "GenX Long-form Model Override",
        "group": "GenX runtime",
        "required": False,
        "secret": False,
    },
    {
        "key_name": "GENX_MODEL_MODERATION",
        "label": "GenX Moderation Model Override",
        "group": "GenX runtime",
        "required": False,
        "secret": False,
    },
    {
        "key_name": "GENX_MODEL_FALLBACKS",
        "label": "GenX Fallback Models",
        "group": "GenX runtime",
        "required": False,
        "secret": False,
    },
    {
        "key_name": "GENX_MODEL_ALLOWLIST",
        "label": "GenX Allowlist",
        "group": "GenX runtime",
        "required": False,
        "secret": False,
    },
    {
        "key_name": "YOUTUBE_CLIENT_ID",
        "label": "YouTube OAuth Client ID",
        "group": "Social OAuth",
        "required": False,
        "secret": True,
    },
    {
        "key_name": "YOUTUBE_CLIENT_SECRET",
        "label": "YouTube OAuth Client Secret",
        "group": "Social OAuth",
        "required": False,
        "secret": True,
    },
    {
        "key_name": "TIKTOK_CLIENT_KEY",
        "label": "TikTok OAuth Client Key",
        "group": "Social OAuth",
        "required": False,
        "secret": True,
    },
    {
        "key_name": "TIKTOK_CLIENT_SECRET",
        "label": "TikTok OAuth Client Secret",
        "group": "Social OAuth",
        "required": False,
        "secret": True,
    },
    {
        "key_name": "META_APP_ID",
        "label": "Meta App ID",
        "group": "Social OAuth",
        "required": False,
        "secret": True,
    },
    {
        "key_name": "META_APP_SECRET",
        "label": "Meta App Secret",
        "group": "Social OAuth",
        "required": False,
        "secret": True,
    },
    {
        "key_name": "TWITTER_CLIENT_ID",
        "label": "Twitter/X OAuth Client ID",
        "group": "Social OAuth",
        "required": False,
        "secret": True,
    },
    {
        "key_name": "TWITTER_CLIENT_SECRET",
        "label": "Twitter/X OAuth Client Secret",
        "group": "Social OAuth",
        "required": False,
        "secret": True,
    },
    {
        "key_name": "LINKEDIN_CLIENT_ID",
        "label": "LinkedIn OAuth Client ID",
        "group": "Social OAuth",
        "required": False,
        "secret": True,
    },
    {
        "key_name": "LINKEDIN_CLIENT_SECRET",
        "label": "LinkedIn OAuth Client Secret",
        "group": "Social OAuth",
        "required": False,
        "secret": True,
    },
    {
        "key_name": "PINTEREST_CLIENT_ID",
        "label": "Pinterest OAuth Client ID",
        "group": "Social OAuth",
        "required": False,
        "secret": True,
    },
    {
        "key_name": "PINTEREST_CLIENT_SECRET",
        "label": "Pinterest OAuth Client Secret",
        "group": "Social OAuth",
        "required": False,
        "secret": True,
    },
    {
        "key_name": "REDDIT_CLIENT_ID",
        "label": "Reddit OAuth Client ID",
        "group": "Social OAuth",
        "required": False,
        "secret": True,
    },
    {
        "key_name": "REDDIT_CLIENT_SECRET",
        "label": "Reddit OAuth Client Secret",
        "group": "Social OAuth",
        "required": False,
        "secret": True,
    },
    {
        "key_name": "SNAPCHAT_CLIENT_ID",
        "label": "Snapchat OAuth Client ID",
        "group": "Social OAuth",
        "required": False,
        "secret": True,
    },
    {
        "key_name": "SNAPCHAT_CLIENT_SECRET",
        "label": "Snapchat OAuth Client Secret",
        "group": "Social OAuth",
        "required": False,
        "secret": True,
    },
]


def mask_value(value: str | None, *, secret: bool = True) -> str:
    if not value:
        return ""
    if not secret:
        return value
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}****{value[-4:]}"


def resolve_user_api_key(db: Session, user_id: str, key_name: str, env_value: str = "") -> str:
    row = db.query(UserAPIKey).filter(
        UserAPIKey.user_id == user_id,
        UserAPIKey.key_name == key_name,
        UserAPIKey.is_active == True,
    ).first()
    if row:
        try:
            return row.get_decrypted_key()
        except Exception:
            return ""
    return env_value or ""
