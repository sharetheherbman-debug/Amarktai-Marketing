"""
App-owned JWT authentication endpoints.

POST /api/v1/auth/register        — create account, return token
POST /api/v1/auth/login           — authenticate, return token
GET  /api/v1/auth/me              — return current user (bearer token required)
POST /api/v1/auth/refresh         — refresh a valid JWT
POST /api/v1/auth/forgot-password — send password-reset email
POST /api/v1/auth/reset-password  — reset password with token
GET  /api/v1/auth/verify-email    — verify email address via token
"""

import logging
import secrets
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.db.base import get_db
from app.models.user import PlanType
from app.models.user import User as UserModel

logger = logging.getLogger(__name__)

router = APIRouter()
bearer_scheme = HTTPBearer()

# Rate limiter — per-endpoint IP-based limits to prevent brute-force attacks
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings as _settings

_limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_settings.REDIS_URL or "memory://",
)


# ── Request / Response schemas ───────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    name: str | None
    is_admin: bool = False
    email_verified: bool = False


# ── Helpers ──────────────────────────────────────────────────────────────────

def _send_email(to: str, subject: str, html: str) -> None:
    """Best-effort email send via Resend API. Failures are logged, not raised."""
    if not _settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not configured — email to %s not sent", to)
        return
    try:
        import httpx
        httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {_settings.RESEND_API_KEY}"},
            json={
                "from": _settings.FROM_EMAIL or "noreply@amarktai.com",
                "to": [to],
                "subject": subject,
                "html": html,
            },
            timeout=10,
        )
    except Exception as exc:
        logger.warning("Failed to send email to %s: %s", to, exc)


def _build_token_response(user: UserModel) -> TokenResponse:
    """Build a consistent token response including admin + verification status."""
    from app.api.deps import is_admin_user
    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        name=user.name,
        is_admin=is_admin_user(user),
        email_verified=getattr(user, "email_verified", False) or False,
    )


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@_limiter.limit("3/minute")
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Register a new user and return an access token."""
    existing = db.query(UserModel).filter(UserModel.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    if len(body.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters.",
        )

    if len(body.password) > 72:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be 72 characters or fewer.",
        )
    user_id = str(uuid.uuid4())
    referral_code = secrets.token_urlsafe(6)
    user = UserModel(
        id=user_id,
        email=body.email,
        hashed_password=hash_password(body.password),
        name=body.name or None,
        plan=PlanType.FREE,
        email_verified=False,
        referral_code=referral_code,
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        logger.exception("Failed to create user %s", body.email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create account.",
        )

    # Send welcome email (non-blocking, failure does not block registration)
    try:
        from app.services.email_service import send_welcome
        send_welcome(user.email, user.name)
    except Exception as exc:
        logger.warning("Welcome email failed for %s: %s", user.email, exc)

    # Send verification email (non-blocking)
    try:
        verify_token = create_access_token(user.id, expires_delta=timedelta(hours=24))
        verify_url = f"{_settings.FRONTEND_URL}/verify-email?token={verify_token}"
        _send_email(
            to=user.email,
            subject="Verify your AmarktAI Marketing account",
            html=(
                f"<h2>Welcome to AmarktAI Marketing!</h2>"
                f"<p>Click the link below to verify your email address:</p>"
                f'<p><a href="{verify_url}">Verify Email</a></p>'
                f"<p>This link expires in 24 hours.</p>"
            ),
        )
    except Exception as exc:
        logger.warning("Verification email failed for %s: %s", user.email, exc)

    # Notify AmarktAI Network of new signup (non-blocking)
    try:
        import asyncio
        from app.services.integration import send_event

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            loop.create_task(send_event("user.signup", {"user_id": user.id}))
        else:
            asyncio.run(send_event("user.signup", {"user_id": user.id}))
    except Exception as exc:
        logger.warning("AmarktAI signup event failed for %s: %s", user.email, exc)

    return _build_token_response(user)


@router.post("/login", response_model=TokenResponse)
@_limiter.limit("5/minute")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate a user and return an access token."""
    logger.info("Login attempt for email=%s", body.email)
    user = db.query(UserModel).filter(UserModel.email == body.email).first()

    if not user or not user.hashed_password:
        logger.warning("Login failed (no user) for email=%s", body.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not verify_password(body.password, user.hashed_password):
        logger.warning("Login failed (bad password) for email=%s", body.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    logger.info("Login success for user_id=%s email=%s", user.id, body.email)
    return _build_token_response(user)


@router.get("/me")
def get_me(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Return the current authenticated user with admin status."""
    user_id = decode_access_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return _build_token_response(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Refresh a valid JWT — returns a new token with a refreshed expiry."""
    user_id = decode_access_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return _build_token_response(user)


@router.get("/verify-email")
def verify_email(
    token: str = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    """Verify a user's email address using a signed JWT link."""
    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification link.")
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user.email_verified = True
    db.commit()
    return {"ok": True, "message": "Email verified successfully."}


@router.post("/forgot-password")
@_limiter.limit("3/minute")
def forgot_password(request: Request, body: ForgotPasswordRequest, db: Session = Depends(get_db)) -> dict:
    """Send a password reset email. Always returns success to avoid email enumeration."""
    user = db.query(UserModel).filter(UserModel.email == body.email).first()
    if user:
        reset_token = create_access_token(user.id, expires_delta=timedelta(hours=1))
        reset_url = f"{_settings.FRONTEND_URL}/reset-password?token={reset_token}"
        _send_email(
            to=user.email,
            subject="Reset your AmarktAI Marketing password",
            html=(
                f"<h2>Password Reset</h2>"
                f"<p>Click the link below to reset your password:</p>"
                f'<p><a href="{reset_url}">Reset Password</a></p>'
                f"<p>This link expires in 1 hour. If you did not request this, ignore this email.</p>"
            ),
        )
    # Always return success to avoid email enumeration
    return {"ok": True, "message": "If an account with that email exists, a reset link has been sent."}


@router.post("/reset-password")
@_limiter.limit("3/minute")
def reset_password(request: Request, body: ResetPasswordRequest, db: Session = Depends(get_db)) -> dict:
    """Reset a user's password using a time-limited JWT token."""
    user_id = decode_access_token(body.token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset link.")

    if len(body.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters.",
        )
    if len(body.new_password) > 72:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be 72 characters or fewer.",
        )

    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.hashed_password = hash_password(body.new_password)
    db.commit()
    return {"ok": True, "message": "Password has been reset successfully."}
