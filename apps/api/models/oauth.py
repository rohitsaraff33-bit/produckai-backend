"""OAuth token storage model."""

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID

from apps.api.database import Base


class OAuthProvider(str, enum.Enum):
    """Supported OAuth providers."""

    google = "google"
    zoom = "zoom"


class TokenStatus(str, enum.Enum):
    """Token status."""

    active = "active"
    revoked = "revoked"
    expired = "expired"


class OAuthToken(Base):
    """Stores encrypted OAuth tokens."""

    __tablename__ = "oauth_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True)  # For future multi-user support
    provider = Column(Enum(OAuthProvider), nullable=False, index=True)
    account_email = Column(String(255), nullable=True)
    scopes = Column(Text, nullable=False)  # Space-separated scopes

    # Encrypted tokens (stored as "nonce|ciphertext")
    access_token_enc = Column(Text, nullable=False)
    refresh_token_enc = Column(Text, nullable=True)

    expires_at = Column(DateTime, nullable=False, index=True)
    status = Column(Enum(TokenStatus), nullable=False, default=TokenStatus.active, index=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<OAuthToken(provider={self.provider}, email={self.account_email}, status={self.status})>"
