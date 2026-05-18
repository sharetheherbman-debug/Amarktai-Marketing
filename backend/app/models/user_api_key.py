"""
User API Keys Model - Stores encrypted user-provided API keys
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base
import base64
from cryptography.fernet import Fernet
from app.core.config import settings


def _build_fernet() -> Fernet | None:
    """Build a Fernet cipher from ENCRYPTION_KEY.

    Fernet requires a 32-byte URL-safe base64-encoded key.  We derive one
    deterministically from whatever string is in settings so that a simple
    passphrase in .env still works.
    """
    raw = settings.ENCRYPTION_KEY
    if not raw or raw == "your-encryption-key-here-change-in-production":
        return None
    # Pad / truncate to exactly 32 bytes then encode as Fernet key
    padded = raw.encode()[:32].ljust(32, b"\0")
    key = base64.urlsafe_b64encode(padded)
    try:
        return Fernet(key)
    except Exception:
        return None


_fernet = _build_fernet()


class UserAPIKey(Base):
    __tablename__ = "user_api_keys"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    key_name = Column(String(128), nullable=False)
    encrypted_key = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    usage_count = Column(String(20), default="0")
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="api_keys")

    @staticmethod
    def encrypt_key(key_value: str) -> str:
        if not _fernet:
            raise RuntimeError("API key encryption is not configured (invalid ENCRYPTION_KEY).")
        return _fernet.encrypt(key_value.encode()).decode()

    @staticmethod
    def decrypt_key(encrypted_value: str) -> str:
        if not _fernet:
            raise RuntimeError("API key decryption is not configured (invalid ENCRYPTION_KEY).")
        try:
            return _fernet.decrypt(encrypted_value.encode()).decode()
        except Exception as exc:
            raise RuntimeError("Stored API key cannot be decrypted with current ENCRYPTION_KEY.") from exc

    def get_decrypted_key(self) -> str:
        return self.decrypt_key(self.encrypted_key)


class UserIntegration(Base):
    """Stores OAuth2 tokens and connection status for social platforms."""
    __tablename__ = "user_integrations"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    platform = Column(String(64), nullable=False)

    encrypted_access_token = Column(Text, nullable=True)
    encrypted_refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)

    is_connected = Column(Boolean, default=False)
    connected_at = Column(DateTime(timezone=True), nullable=True)
    disconnected_at = Column(DateTime(timezone=True), nullable=True)

    platform_user_id = Column(String(255), nullable=True)
    platform_username = Column(String(255), nullable=True)
    platform_data = Column(Text, nullable=True)
    scopes = Column(Text, nullable=True)

    auto_post_enabled = Column(Boolean, default=False)
    auto_reply_enabled = Column(Boolean, default=False)
    low_risk_auto_reply = Column(Boolean, default=False)

    # OAuth state management (PKCE / CSRF)
    oauth_state = Column(String(255), nullable=True, index=True)
    oauth_code_verifier = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="integrations")

    def get_access_token(self) -> str | None:
        if self.encrypted_access_token:
            if not _fernet:
                raise RuntimeError("Integration token decryption is not configured (invalid ENCRYPTION_KEY).")
            try:
                return _fernet.decrypt(self.encrypted_access_token.encode()).decode()
            except Exception as exc:
                raise RuntimeError("Stored integration access token cannot be decrypted.") from exc
        return self.encrypted_access_token

    def get_refresh_token(self) -> str | None:
        if self.encrypted_refresh_token:
            if not _fernet:
                raise RuntimeError("Integration token decryption is not configured (invalid ENCRYPTION_KEY).")
            try:
                return _fernet.decrypt(self.encrypted_refresh_token.encode()).decode()
            except Exception as exc:
                raise RuntimeError("Stored integration refresh token cannot be decrypted.") from exc
        return self.encrypted_refresh_token

    @staticmethod
    def encrypt_token(token: str) -> str:
        if token:
            if not _fernet:
                raise RuntimeError("Integration token encryption is not configured (invalid ENCRYPTION_KEY).")
            return _fernet.encrypt(token.encode()).decode()
        return token
