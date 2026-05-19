from pydantic_settings import BaseSettings
from typing import List
import logging as _logging
import os

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "AmarktAI Marketing"
    DEBUG: bool = False
    FRONTEND_URL: str = "https://marketing.amarktai.com"
    ADMIN_USER_IDS: str = ""  # comma-separated list of admin user IDs
    # Platform owner's email — always granted unlimited access at no cost.
    # Override via ADMIN_EMAIL env var to change the admin for a different deployment.
    ADMIN_EMAIL: str = "amarktainetwork@gmail.com"
    
    # Database (PostgreSQL is the canonical database for this project)
    # Database
    DATABASE_URL: str = "postgresql://amarktai:CHANGE_THIS_PASSWORD@localhost:5432/amarktai"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # CORS — include localhost for development and the production domain
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://marketing.amarktai.com",
    ]
    
    # App-owned JWT Auth
    # Generate with: openssl rand -hex 32
    JWT_SECRET: str = "change-me-in-production-use-openssl-rand-hex-32"

    # Encryption (for API keys and tokens)
    ENCRYPTION_KEY: str = "your-encryption-key-here-change-in-production"
    
    # ==================== LLM API KEYS ====================
    # GenX (primary unified AI provider)
    GENX_API_KEY: str = ""
    GENX_BASE_URL: str = "https://api.genxai.co/v1"
    GENX_DEFAULT_MODEL: str = "genx-chat-pro"
    GENX_TIMEOUT: int = 60
    GENX_MODEL_ALLOWLIST: str = ""  # comma-separated model IDs
    GENX_MODEL_FALLBACKS: str = ""  # comma-separated ordered fallback model IDs
    GENX_MODEL_COPY: str = ""
    GENX_MODEL_STRATEGY: str = ""
    GENX_MODEL_ANALYSIS: str = ""
    GENX_MODEL_LONG_FORM: str = ""
    GENX_MODEL_MODERATION: str = ""
    GENX_MODEL_IMAGE: str = ""
    GENX_MODEL_VIDEO: str = ""
    GENX_MODEL_AUDIO: str = ""

    # Primary LLM providers
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GROQ_API_KEY: str = ""  # Fast inference

    # AI provider config
    QWEN_API_KEY: str = ""
    QWEN_MODEL: str = "Qwen/Qwen2.5-72B-Instruct"
    
    # Gemini (Google) — optional add-on
    GOOGLE_GEMINI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""  # alias used by ai_provider
    GOOGLE_AI_API_KEY: str = ""  # Legacy
    
    # Grok/X AI
    GROK_API_KEY: str = ""
    XAI_API_KEY: str = ""  # Alternative
    
    # ==================== MEDIA GENERATION API KEYS ====================
    # Image Generation
    LEONARDO_API_KEY: str = ""  # Leonardo.AI
    OPENAI_DALLE_KEY: str = ""  # DALL-E
    MIDJOURNEY_API_KEY: str = ""  # Midjourney (via API)
    STABILITY_API_KEY: str = ""  # Stability AI
    
    # Free/Cheap alternatives
    HUGGINGFACE_TOKEN: str = ""
    FAL_AI_KEY: str = ""  # fal.ai
    SILICONFLOW_API_KEY: str = ""  # SiliconFlow
    REPLICATE_API_TOKEN: str = ""  # Replicate
    
    # Video Generation
    RUNWAY_API_KEY: str = ""  # Runway ML
    HEYGEN_API_KEY: str = ""  # HeyGen
    SYNTHESIA_API_KEY: str = ""  # Synthesia
    
    # Audio/Voice
    ELEVENLABS_API_KEY: str = ""  # ElevenLabs
    COQUI_API_KEY: str = ""  # Coqui TTS (free alternative)
    PLAYHT_API_KEY: str = ""  # Play.ht
    
    # ==================== SOCIAL PLATFORM API KEYS ====================
    # YouTube
    YOUTUBE_CLIENT_ID: str = ""
    YOUTUBE_CLIENT_SECRET: str = ""
    YOUTUBE_API_KEY: str = ""  # For read operations
    
    # TikTok
    TIKTOK_CLIENT_KEY: str = ""
    TIKTOK_CLIENT_SECRET: str = ""
    TIKTOK_APP_ID: str = ""
    
    # Meta (Instagram + Facebook)
    META_APP_ID: str = ""
    META_APP_SECRET: str = ""
    INSTAGRAM_CLIENT_ID: str = ""
    INSTAGRAM_CLIENT_SECRET: str = ""
    FACEBOOK_CLIENT_ID: str = ""
    FACEBOOK_CLIENT_SECRET: str = ""
    
    # Twitter/X
    TWITTER_CLIENT_ID: str = ""
    TWITTER_CLIENT_SECRET: str = ""
    TWITTER_API_KEY: str = ""  # v1.1 API
    TWITTER_API_SECRET: str = ""
    TWITTER_BEARER_TOKEN: str = ""
    
    # LinkedIn
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""

    # Pinterest
    PINTEREST_CLIENT_ID: str = ""
    PINTEREST_CLIENT_SECRET: str = ""

    # Reddit (also used for trend analysis)
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "AmarktAIBot/1.0"

    # Bluesky / AT Protocol
    BLUESKY_CLIENT_ID: str = ""
    BLUESKY_IDENTIFIER: str = ""  # handle e.g. user.bsky.social
    BLUESKY_APP_PASSWORD: str = ""

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHANNEL_ID: str = ""  # @channel or numeric chat_id

    # Snapchat
    SNAPCHAT_CLIENT_ID: str = ""
    SNAPCHAT_CLIENT_SECRET: str = ""

    # ==================== TREND DATA SOURCES ====================
    # Google Trends
    GOOGLE_TRENDS_API_KEY: str = ""
    
    # News APIs (for content ideas)
    NEWSAPI_KEY: str = ""
    GNEWS_API_KEY: str = ""
    
    # ==================== WEB SCRAPING ====================
    # Web scraping (optional external provider)
    FIRECRAWL_API_KEY: str = ""
    
    # ==================== PAYMENTS ====================
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_ID_FREE: str = ""
    STRIPE_PRICE_ID_PRO: str = ""
    STRIPE_PRICE_ID_BUSINESS: str = ""
    STRIPE_PRICE_ID_ENTERPRISE: str = ""
    
    # ==================== EMAIL ====================
    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = "noreply@amarktai.com"
    CONTACT_EMAIL: str = ""  # Destination for contact form submissions
    
    # ==================== STORAGE ====================
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_BUCKET: str = "amarktai-media"
    
    # AWS S3 (alternative)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_BUCKET: str = ""
    AWS_REGION: str = "us-east-1"
    
    # ==================== AMARKTAI NETWORK INTEGRATION ====================
    # Per-app identity
    APP_ID: str = "amarktai-marketing"
    APP_SLUG: str = "amarktai-marketing"
    APP_VERSION: str = "1.0.0"
    APP_ENVIRONMENT: str = "production"  # production | staging | development

    # Outbound integration (connection to AmarktAI Network main dashboard)
    # Keep AMARKTAI_INTEGRATION_TOKEN server-side only — never expose to frontend
    AMARKTAI_DASHBOARD_URL: str = ""   # e.g. https://dashboard.amarktai.com
    AMARKTAI_INTEGRATION_TOKEN: str = ""  # generated per-app token in AmarktAI Network
    AMARKTAI_INTEGRATION_ENABLED: bool = False

    # ==================== MONITORING ====================
    SENTRY_DSN: str = ""
    
    # ==================== FEATURE FLAGS ====================
    ENABLE_AUTO_POST: bool = False  # Enable autonomous posting
    ENABLE_AUTO_REPLY: bool = False  # Enable auto-replies
    ENABLE_AB_TESTING: bool = True
    ENABLE_VIRAL_PREDICTION: bool = True
    ENABLE_COST_TRACKING: bool = True
    
    # ==================== RATE LIMITS ====================
    MAX_CONTENT_PER_DAY: int = 10  # Per user
    MAX_ENGAGEMENT_REPLIES_PER_DAY: int = 50
    MAX_MEDIA_GENERATIONS_PER_DAY: int = 20

    # ==================== MEDIA UPLOAD ====================
    # Local filesystem directory for uploaded brand media assets.
    # In production this should be a persistent volume, e.g. /var/www/media.
    # Served by FastAPI StaticFiles at the /media path.
    MEDIA_UPLOAD_DIR: str = "/tmp/amarktai_media"

    # ==================== BUSINESS LIMITS ====================
    MAX_BUSINESSES_PER_USER: int = 20  # Max web apps / businesses per account
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

# ── Security checks for production ───────────────────────────────────────────
# ── Production-safety checks ─────────────────────────────────────────────────
import logging as _logging
_cfg_logger = _logging.getLogger(__name__)

_DEFAULT_JWT_SECRET = "change-me-in-production-use-openssl-rand-hex-32"
_DEFAULT_ENCRYPTION_KEY = "your-encryption-key-here-change-in-production"
_is_production = settings.APP_ENVIRONMENT == "production"

_security_logger = _logging.getLogger(__name__)

if settings.JWT_SECRET == _DEFAULT_JWT_SECRET:
    if _is_production:
        _security_logger.critical(
            "FATAL: JWT_SECRET is set to the insecure default value in PRODUCTION mode. "
            "Set JWT_SECRET in your .env file using: openssl rand -hex 32"
        )
        raise SystemExit(
            "Refusing to start: JWT_SECRET must be changed from the default value in production. "
            "Run: openssl rand -hex 32"
        )
    else:
        _security_logger.warning(
            "JWT_SECRET is set to the default insecure value. "
            "Set JWT_SECRET in your .env file using: openssl rand -hex 32"
        )

if settings.ENCRYPTION_KEY == _DEFAULT_ENCRYPTION_KEY:
    if _is_production:
        _security_logger.critical(
            "FATAL: ENCRYPTION_KEY is set to the insecure default value in PRODUCTION mode. "
            "Set ENCRYPTION_KEY in your .env file using: openssl rand -base64 32"
        )
        raise SystemExit(
            "Refusing to start: ENCRYPTION_KEY must be changed from the default value in production. "
            "Run: openssl rand -base64 32"
        )
    else:
        _security_logger.warning(
            "ENCRYPTION_KEY is set to the default insecure value. "
            "Set ENCRYPTION_KEY in your .env file using: openssl rand -base64 32"
        )
# Guard against default DB password in production
_db_url = settings.DATABASE_URL or ""
if _is_production and ("changeme" in _db_url.lower() or "CHANGE_THIS_PASSWORD" in _db_url):
    raise RuntimeError(
        "FATAL: DATABASE_URL contains a default password. "
        "Set POSTGRES_PASSWORD in your .env file before deploying."
    )

# Warn when ADMIN_EMAIL is still the default shipping value in production.
# This is only a warning (not a hard stop) because the owner may intentionally
# keep the official address; third-party deployments should override it.
_DEFAULT_ADMIN_EMAIL = "amarktainetwork@gmail.com"
if _is_production and settings.ADMIN_EMAIL == _DEFAULT_ADMIN_EMAIL:
    _security_logger.warning(
        "ADMIN_EMAIL is still set to the default value '%s'. "
        "Override ADMIN_EMAIL in your .env file if this is not the intended admin account.",
        _DEFAULT_ADMIN_EMAIL,
    )

# Warn when GenX (primary AI provider) is not configured in production.
if _is_production and not settings.GENX_API_KEY:
    _security_logger.warning(
        "GENX_API_KEY is not set. GenX is the primary AI provider — "
        "content generation will fall back to secondary providers or templates. "
        "Set GENX_API_KEY in your .env file for full functionality."
    )
