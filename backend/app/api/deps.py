"""
Authentication dependency for FastAPI endpoints.

Uses app-owned JWT (HS256) issued by /api/v1/auth/login and /api/v1/auth/register.
Set JWT_SECRET in backend .env (generate with: openssl rand -hex 32).
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.core.config import settings
from app.db.base import get_db
from app.models.user import PlanType, User

_bearer = HTTPBearer(auto_error=False)


def is_admin_user(user: User) -> bool:
    """Return True if the user has admin privileges (unlimited access, no cost).

    Admin status is determined by:
      1. The user's email matching ADMIN_EMAIL (set via env var), OR
      2. The user's ID appearing in ADMIN_USER_IDS (comma-separated env var).
    """
    admin_email = (settings.ADMIN_EMAIL or "amarktainetwork@gmail.com").lower()
    if user.email and user.email.lower() == admin_email:
        return True
    admin_ids_raw = os.getenv("ADMIN_USER_IDS", "")
    admin_ids = {uid.strip() for uid in admin_ids_raw.split(",") if uid.strip()}
    return user.id in admin_ids


def effective_plan_name(user: User) -> str:
    if is_admin_user(user):
        return PlanType.ENTERPRISE.value
    plan = getattr(user, "plan", PlanType.FREE)
    return plan.value if hasattr(plan, "value") else str(plan or PlanType.FREE.value)


def effective_quota_limit(user: User) -> int:
    if is_admin_user(user):
        return 99999
    return _PLAN_QUOTA_MAP.get(effective_plan_name(user), 50)


def admin_access_snapshot(user: User) -> dict[str, object]:
    is_admin = is_admin_user(user)
    return {
        "is_admin": is_admin,
        "effective_plan": effective_plan_name(user),
        "unlimited_content_quota": is_admin,
        "unlimited_business_count": is_admin,
        "unrestricted_provider_access": is_admin,
        "billing_enabled": bool(settings.ENABLE_BILLING and not is_admin),
        "show_billing_prompts": bool(settings.ENABLE_BILLING and not is_admin),
    }


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency that returns the authenticated User model.

    Requires a valid JWT Bearer token issued by this app.
    Raises HTTP 401 if the token is missing or invalid,
    and HTTP 404 if the user record no longer exists.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = decode_access_token(credentials.credentials)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return user


async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency that ensures the current user is an admin.
    Admin status is determined by:
      1. The ADMIN_USER_IDS env var (comma-separated user IDs), OR
      2. The user's email matching ADMIN_EMAIL (platform owner).
    Admin users bypass all cost/quota restrictions.
    """
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# ── Plan quota enforcement ───────────────────────────────────────────────────

_PLAN_QUOTA_MAP: dict[str, int] = {
    "free": 50,
    "pro": 500,
    "business": 2000,
    "enterprise": 99999,
}


async def enforce_content_quota(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency that checks the user's plan quota before content generation.
    Admins bypass quota checks. Returns HTTP 429 when quota is exceeded.
    """
    if is_admin_user(current_user):
        return current_user

    plan = effective_plan_name(current_user)
    used = getattr(current_user, "monthly_content_used", 0) or 0
    limit = effective_quota_limit(current_user)

    if used >= limit:
        upgrade_message = "Contact admin to extend access."
        if settings.ENABLE_BILLING:
            upgrade_message = "Upgrade your plan at /pricing to generate more content."
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Monthly content quota exceeded ({used}/{limit}). "
                f"{upgrade_message}"
            ),
        )

    return current_user
