"""
API Keys & Integrations Endpoints
"""

import logging
from datetime import timedelta
import uuid
from datetime import datetime
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user_api_key import UserAPIKey, UserIntegration
from app.models.user import User
from app.core.config import settings
from app.services.provider_catalog import USER_PROVIDER_KEY_NAMES
from app.services.platform_catalog import platform_catalog, platform_label
from app.services.posting_readiness import platform_posting_state

logger = logging.getLogger(__name__)
router = APIRouter()

# Schemas
class APIKeyCreate(BaseModel):
    key_name: str
    key_value: str

class APIKeyResponse(BaseModel):
    id: str
    key_name: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class IntegrationStatus(BaseModel):
    id: str
    label: str
    content_generation_available: bool
    oauth_supported: bool
    oauth_configured: bool
    user_connected: bool
    token_valid: bool
    scopes_ok: bool
    posting_supported: bool
    can_post_now: bool
    missing: list[str]
    status_label: str
    user_message: str

class IntegrationUpdate(BaseModel):
    auto_post_enabled: bool = None
    auto_reply_enabled: bool = None
    low_risk_auto_reply: bool = None

# API Keys Endpoints
@router.get("/api-keys", response_model=List[APIKeyResponse])
async def get_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all API keys for the current user (values are hidden)."""
    keys = db.query(UserAPIKey).filter(
        UserAPIKey.user_id == current_user.id,
        UserAPIKey.is_active == True
    ).all()
    
    return [
        {
            "id": key.id,
            "key_name": key.key_name,
            "is_active": key.is_active,
            "created_at": key.created_at
        }
        for key in keys
    ]

@router.post("/api-keys", status_code=status.HTTP_201_CREATED)
async def create_api_key(
    api_key: APIKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a new API key for the current user."""
    # Validate key name
    if api_key.key_name not in USER_PROVIDER_KEY_NAMES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid key name. Must be one of: {', '.join(sorted(USER_PROVIDER_KEY_NAMES))}"
        )
    
    # Check if key already exists
    existing = db.query(UserAPIKey).filter(
        UserAPIKey.user_id == current_user.id,
        UserAPIKey.key_name == api_key.key_name
    ).first()
    
    if existing:
        # Update existing key
        existing.encrypted_key = UserAPIKey.encrypt_key(api_key.key_value)
        existing.is_active = True
        existing.updated_at = datetime.now()
    else:
        # Create new key
        new_key = UserAPIKey(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            key_name=api_key.key_name,
            encrypted_key=UserAPIKey.encrypt_key(api_key.key_value),
            is_active=True
        )
        db.add(new_key)
    
    db.commit()
    
    return {"message": "API key saved successfully"}

@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete (deactivate) an API key."""
    key = db.query(UserAPIKey).filter(
        UserAPIKey.id == key_id,
        UserAPIKey.user_id == current_user.id
    ).first()
    
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    key.is_active = False
    db.commit()
    
    return {"message": "API key deleted successfully"}

# Platform Integrations Endpoints
@router.get("/platforms", response_model=List[IntegrationStatus])
async def get_integrations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get launch platform readiness with safe, non-failing output."""
    platforms = platform_catalog()
    result: list[dict[str, Any]] = []
    for platform_meta in platforms:
        platform = platform_meta["id"]
        try:
            state = platform_posting_state(db, current_user.id, platform)
        except Exception as exc:
            logger.warning("Platform readiness failed for user %s platform %s: %s", current_user.id, platform, str(exc)[:300])
            state = {
                "oauth_configured": False,
                "user_connected": False,
                "token_valid": False,
                "scopes_ok": False,
                "posting_supported": False,
                "can_post_now": False,
                "missing": ["oauth_config"],
            }

        oauth_supported = bool(platform_meta.get("oauth_supported", True))
        oauth_configured = bool(state.get("oauth_configured", platform_meta.get("oauth_configured", False)))
        posting_supported = bool(state.get("posting_supported", False))
        can_post_now = bool(state.get("can_post_now", False))
        missing = list(state.get("missing", [])) if isinstance(state.get("missing", []), list) else []

        if can_post_now:
            status_label = "Ready to post"
            user_message = "OAuth and posting requirements are configured."
        elif not oauth_configured:
            status_label = "OAuth not configured"
            user_message = str(platform_meta.get("user_message", "Content generation is available."))
        elif not posting_supported:
            status_label = "Generation only"
            user_message = str(platform_meta.get("user_message", "Content generation is available."))
        elif not bool(state.get("user_connected", False)):
            status_label = "Posting not configured"
            user_message = "Content generation is available. Connect OAuth to enable posting."
        else:
            status_label = "Limited mode"
            user_message = "Content generation is available. Complete posting requirements to publish."

        result.append({
            "id": platform,
            "label": platform_label(platform),
            "content_generation_available": True,
            "oauth_supported": oauth_supported,
            "oauth_configured": oauth_configured,
            "user_connected": bool(state.get("user_connected", False)),
            "token_valid": bool(state.get("token_valid", False)),
            "scopes_ok": bool(state.get("scopes_ok", False)),
            "posting_supported": posting_supported,
            "can_post_now": can_post_now,
            "missing": missing,
            "status_label": status_label,
            "user_message": user_message,
        })

    return result

@router.get("/platforms/{platform}/connect")
async def connect_platform(
    platform: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get OAuth2 authorization URL for a platform."""
    platform_configs = {
        "youtube": {
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "client_id": settings.YOUTUBE_CLIENT_ID,
            "scope": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"
        },
        "twitter": {
            "auth_url": "https://twitter.com/i/oauth2/authorize",
            "client_id": settings.TWITTER_CLIENT_ID,
            "scope": "tweet.read tweet.write users.read offline.access"
        },
        "linkedin": {
            "auth_url": "https://www.linkedin.com/oauth/v2/authorization",
            "client_id": settings.LINKEDIN_CLIENT_ID,
            "scope": "r_liteprofile r_basicprofile w_member_social"
        },
        "instagram": {
            "auth_url": "https://www.facebook.com/v18.0/dialog/oauth",
            "client_id": settings.META_APP_ID,
            "scope": "instagram_basic instagram_content_publish"
        },
        "facebook": {
            "auth_url": "https://www.facebook.com/v18.0/dialog/oauth",
            "client_id": settings.META_APP_ID,
            "scope": "pages_manage_posts pages_read_engagement"
        },
        "tiktok": {
            "auth_url": "https://www.tiktok.com/auth/authorize",
            "client_id": settings.TIKTOK_CLIENT_KEY,
            "scope": "video.upload video.list"
        },
        "pinterest": {
            "auth_url": "https://www.pinterest.com/oauth/",
            "client_id": settings.PINTEREST_CLIENT_ID,
            "scope": "boards:read pins:read pins:write"
        },
        "reddit": {
            "auth_url": "https://www.reddit.com/api/v1/authorize",
            "client_id": settings.REDDIT_CLIENT_ID,
            "scope": "identity submit read"
        },
        "bluesky": {
            "auth_url": "https://bsky.social/oauth/authorize",
            "client_id": settings.BLUESKY_CLIENT_ID,
            "scope": "atproto"
        },
        "threads": {
            "auth_url": "https://www.threads.net/oauth/authorize",
            "client_id": settings.META_APP_ID,
            "scope": "threads_basic threads_content_publish"
        },
        "telegram": {
            "auth_url": "https://oauth.telegram.org/auth",
            "client_id": settings.TELEGRAM_BOT_TOKEN,
            "scope": "messages"
        },
        "snapchat": {
            "auth_url": "https://accounts.snapchat.com/accounts/oauth2/auth",
            "client_id": settings.SNAPCHAT_CLIENT_ID,
            "scope": "snapchat-marketing-api"
        },
    }
    
    config = platform_configs.get(platform)
    if not config:
        raise HTTPException(status_code=400, detail="Invalid platform")
    
    if not config["client_id"]:
        raise HTTPException(status_code=503, detail=f"{platform} OAuth not configured")
    
    # Build authorization URL with cryptographically secure state token
    import secrets
    from urllib.parse import urlencode

    # Generate a cryptographically random state token and map it to user_id:platform
    state_token = secrets.token_urlsafe(32)
    # Store the state → user mapping in a temporary DB record or in-memory cache.
    # We use a lightweight approach: store as a pending integration record.
    pending = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.platform == platform,
    ).first()
    if not pending:
        pending = UserIntegration(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            platform=platform,
        )
        db.add(pending)
    # Store the state token as oauth_state for verification at callback
    pending.oauth_state = state_token
    pending.is_connected = False
    pending.scopes = config.get("scope")

    # For Twitter PKCE, generate and store the code_verifier
    code_verifier = None
    code_challenge = None
    if platform == "twitter":
        import hashlib
        import base64
        code_verifier = secrets.token_urlsafe(43)
        pending.oauth_code_verifier = code_verifier
        digest = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

    db.commit()

    params = {
        "client_id": config["client_id"],
        "redirect_uri": f"{settings.FRONTEND_URL.rstrip('/')}/api/v1/integrations/platforms/callback",
        "scope": config["scope"],
        "response_type": "code",
        "state": state_token,
        "access_type": "offline",
        "prompt": "consent",
    }

    if code_challenge:
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"

    auth_url = f"{config['auth_url']}?{urlencode(params)}"

    return {"auth_url": auth_url}

@router.post("/platforms/{platform}/disconnect")
async def disconnect_platform(
    platform: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Disconnect a platform integration."""
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.platform == platform
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    integration.is_connected = False
    integration.disconnected_at = datetime.now()
    integration.encrypted_access_token = None
    integration.encrypted_refresh_token = None
    
    db.commit()
    
    return {"message": f"{platform} disconnected successfully"}

@router.patch("/platforms/{platform}")
async def update_integration(
    platform: str,
    update: IntegrationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update integration settings."""
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.platform == platform
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if update.auto_post_enabled is not None:
        integration.auto_post_enabled = update.auto_post_enabled
    if update.auto_reply_enabled is not None:
        integration.auto_reply_enabled = update.auto_reply_enabled
    if update.low_risk_auto_reply is not None:
        integration.low_risk_auto_reply = update.low_risk_auto_reply
    
    db.commit()
    
    return {"message": "Integration updated successfully"}

@router.api_route("/platforms/callback", methods=["GET", "POST"])
async def oauth_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    """Handle OAuth2 callback from platforms — exchanges code for access token."""
    # Validate the state token against stored server-side mapping
    integration = db.query(UserIntegration).filter(
        UserIntegration.oauth_state == state,
    ).first()

    if not integration:
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter. Please reconnect.")

    user_id = integration.user_id
    platform = integration.platform

    # Clear the state token (one-time use)
    stored_code_verifier = getattr(integration, "oauth_code_verifier", None)
    integration.oauth_state = None
    integration.oauth_code_verifier = None
    db.flush()

    # Exchange code for tokens (platform-specific)
    token_endpoints: dict[str, dict] = {
        "youtube": {
            "url": "https://oauth2.googleapis.com/token",
            "client_id": settings.YOUTUBE_CLIENT_ID,
            "client_secret": settings.YOUTUBE_CLIENT_SECRET,
        },
        "twitter": {
            "url": "https://api.twitter.com/2/oauth2/token",
            "client_id": settings.TWITTER_CLIENT_ID,
            "client_secret": settings.TWITTER_CLIENT_SECRET,
        },
        "linkedin": {
            "url": "https://www.linkedin.com/oauth/v2/accessToken",
            "client_id": settings.LINKEDIN_CLIENT_ID,
            "client_secret": settings.LINKEDIN_CLIENT_SECRET,
        },
        "instagram": {
            "url": "https://graph.facebook.com/v18.0/oauth/access_token",
            "client_id": settings.META_APP_ID,
            "client_secret": settings.META_APP_SECRET,
        },
        "facebook": {
            "url": "https://graph.facebook.com/v18.0/oauth/access_token",
            "client_id": settings.META_APP_ID,
            "client_secret": settings.META_APP_SECRET,
        },
        "tiktok": {
            "url": "https://open.tiktokapis.com/v2/oauth/token/",
            "client_id": settings.TIKTOK_CLIENT_KEY,
            "client_secret": settings.TIKTOK_CLIENT_SECRET,
        },
        "pinterest": {
            "url": "https://api.pinterest.com/v5/oauth/token",
            "client_id": settings.PINTEREST_CLIENT_ID,
            "client_secret": settings.PINTEREST_CLIENT_SECRET,
        },
        "reddit": {
            "url": "https://www.reddit.com/api/v1/access_token",
            "client_id": settings.REDDIT_CLIENT_ID,
            "client_secret": settings.REDDIT_CLIENT_SECRET,
        },
        "threads": {
            "url": "https://graph.threads.net/oauth/access_token",
            "client_id": settings.META_APP_ID,
            "client_secret": settings.META_APP_SECRET,
        },
        "snapchat": {
            "url": "https://accounts.snapchat.com/accounts/oauth2/token",
            "client_id": settings.SNAPCHAT_CLIENT_ID,
            "client_secret": settings.SNAPCHAT_CLIENT_SECRET,
        },
    }

    import httpx as _httpx

    access_token = None
    refresh_token = None
    platform_username = None

    cfg = token_endpoints.get(platform)
    if cfg and cfg.get("client_id") and cfg.get("client_secret"):
        redirect_uri = f"{settings.FRONTEND_URL.rstrip('/')}/api/v1/integrations/platforms/callback"
        try:
            async with _httpx.AsyncClient(timeout=20) as client:
                if platform == "reddit":
                    # Reddit uses HTTP Basic Auth
                    resp = await client.post(
                        cfg["url"],
                        data={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri},
                        auth=(cfg["client_id"], cfg["client_secret"]),
                        headers={"User-Agent": settings.REDDIT_USER_AGENT},
                    )
                elif platform == "twitter":
                    import base64 as _b64
                    creds = _b64.b64encode(f"{cfg['client_id']}:{cfg['client_secret']}".encode()).decode()
                    # Use the server-stored code_verifier from the OAuth initiation
                    code_verifier = stored_code_verifier
                    if not code_verifier:
                        logger.warning("No stored code_verifier for Twitter PKCE — callback may fail")
                        import secrets as _secrets
                        code_verifier = _secrets.token_urlsafe(43)
                    resp = await client.post(
                        cfg["url"],
                        data={"grant_type": "authorization_code", "code": code,
                              "redirect_uri": redirect_uri, "code_verifier": code_verifier},
                        headers={"Authorization": f"Basic {creds}", "Content-Type": "application/x-www-form-urlencoded"},
                    )
                else:
                    resp = await client.post(
                        cfg["url"],
                        data={
                            "grant_type": "authorization_code",
                            "code": code,
                            "redirect_uri": redirect_uri,
                            "client_id": cfg["client_id"],
                            "client_secret": cfg["client_secret"],
                        },
                    )
                if resp.is_success:
                    data = resp.json()
                    access_token = data.get("access_token")
                    refresh_token = data.get("refresh_token")
                    returned_scope = data.get("scope")
                    expires_in = data.get("expires_in")
                else:
                    logger.warning("OAuth token exchange failed for %s: %s", platform, resp.text)
        except Exception as exc:
            logger.warning("OAuth error for %s: %s", platform, exc)

    # Store tokens
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == user_id,
        UserIntegration.platform == platform
    ).first()

    if not integration:
        integration = UserIntegration(
            id=str(uuid.uuid4()),
            user_id=user_id,
            platform=platform
        )
        db.add(integration)

    integration.is_connected = bool(access_token)
    integration.connected_at = datetime.now() if access_token else None
    if locals().get("returned_scope"):
        integration.scopes = str(returned_scope)
    if locals().get("expires_in"):
        try:
            integration.token_expires_at = datetime.now() + timedelta(seconds=int(expires_in))
        except Exception:
            pass

    if access_token:
        integration.encrypted_access_token = UserIntegration.encrypt_token(access_token)
    if refresh_token:
        integration.encrypted_refresh_token = UserIntegration.encrypt_token(refresh_token)

    db.commit()

    return {
        "ok": bool(access_token),
        "platform": platform,
        "message": "Connection complete.",
    }
