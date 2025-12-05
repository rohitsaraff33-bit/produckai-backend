"""OAuth integration endpoints for external services."""

import secrets
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.config import get_settings
from apps.api.database import get_db
from apps.api.models import OAuthProvider, OAuthToken, TokenStatus
from apps.api.services.crypto import get_token_encryptor

logger = structlog.get_logger()
router = APIRouter()
settings = get_settings()

# In-memory state storage (in production, use Redis)
_oauth_states: dict[str, dict] = {}


class IntegrationStatus(BaseModel):
    """Integration status response."""

    provider: str
    connected: bool
    account_email: Optional[str] = None
    scopes: Optional[str] = None
    expires_at: Optional[datetime] = None


class OAuthAuthorizeResponse(BaseModel):
    """OAuth authorization URL response."""

    authorization_url: str
    state: str


@router.get("/integrations", response_model=list[IntegrationStatus])
async def list_integrations(db: Session = Depends(get_db)):
    """
    List all integration statuses.

    Returns:
        List of integration statuses (Zoom, Google, etc.)
    """
    integrations = []
    now = datetime.utcnow()

    # Check Zoom
    zoom_token = (
        db.query(OAuthToken)
        .filter(
            OAuthToken.provider == OAuthProvider.zoom,
            OAuthToken.status == TokenStatus.active,
            OAuthToken.expires_at > now,  # Check token is not expired
        )
        .first()
    )
    integrations.append(
        IntegrationStatus(
            provider="zoom",
            connected=zoom_token is not None,
            account_email=zoom_token.account_email if zoom_token else None,
            scopes=zoom_token.scopes if zoom_token else None,
            expires_at=zoom_token.expires_at if zoom_token else None,
        )
    )

    # Check Google
    google_token = (
        db.query(OAuthToken)
        .filter(
            OAuthToken.provider == OAuthProvider.google,
            OAuthToken.status == TokenStatus.active,
            OAuthToken.expires_at > now,  # Check token is not expired
        )
        .first()
    )
    integrations.append(
        IntegrationStatus(
            provider="google",
            connected=google_token is not None,
            account_email=google_token.account_email if google_token else None,
            scopes=google_token.scopes if google_token else None,
            expires_at=google_token.expires_at if google_token else None,
        )
    )

    return integrations


@router.get("/integrations/zoom/authorize", response_model=OAuthAuthorizeResponse)
async def authorize_zoom():
    """
    Start Zoom OAuth flow.

    Returns:
        Authorization URL to redirect user to
    """
    if not settings.zoom_client_id or not settings.zoom_client_secret:
        raise HTTPException(
            status_code=500,
            detail="Zoom OAuth is not configured. Please set ZOOM_CLIENT_ID and ZOOM_CLIENT_SECRET.",
        )

    # Generate random state for CSRF protection
    state = secrets.token_urlsafe(32)

    # Store state in memory (use Redis in production)
    _oauth_states[state] = {
        "provider": "zoom",
        "created_at": datetime.utcnow(),
    }

    # Build authorization URL
    redirect_uri = f"{settings.oauth_redirect_base_url}/auth/zoom/callback"
    params = {
        "response_type": "code",
        "client_id": settings.zoom_client_id,
        "redirect_uri": redirect_uri,
        "state": state,
    }
    auth_url = f"https://zoom.us/oauth/authorize?{urlencode(params)}"

    logger.info("Starting Zoom OAuth flow", state=state, redirect_uri=redirect_uri)

    return OAuthAuthorizeResponse(authorization_url=auth_url, state=state)


@router.get("/auth/zoom/callback")
async def zoom_callback(
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="OAuth state"),
    db: Session = Depends(get_db),
):
    """
    Handle Zoom OAuth callback.

    Args:
        code: Authorization code from Zoom
        state: OAuth state for CSRF protection
        db: Database session

    Returns:
        Success message
    """
    # Verify state
    if state not in _oauth_states:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    state_data = _oauth_states.pop(state)

    # Check state expiration (5 minutes)
    if datetime.utcnow() - state_data["created_at"] > timedelta(minutes=5):
        raise HTTPException(status_code=400, detail="OAuth state expired")

    # Exchange code for tokens
    redirect_uri = f"{settings.oauth_redirect_base_url}/auth/zoom/callback"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://zoom.us/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                auth=(settings.zoom_client_id, settings.zoom_client_secret),
            )
            response.raise_for_status()
            token_data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error("Failed to exchange Zoom code for token", error=str(e))
            raise HTTPException(status_code=400, detail="Failed to exchange authorization code")

    # Get user info
    access_token = token_data["access_token"]
    try:
        async with httpx.AsyncClient() as client:
            user_response = await client.get(
                "https://api.zoom.us/v2/users/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            user_response.raise_for_status()
            user_data = user_response.json()
            account_email = user_data.get("email", "")
    except Exception as e:
        logger.warning("Failed to fetch Zoom user info", error=str(e))
        account_email = ""

    # Encrypt and store tokens
    encryptor = get_token_encryptor()

    expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])

    # Revoke any existing active tokens for this provider
    db.query(OAuthToken).filter(
        OAuthToken.provider == OAuthProvider.zoom,
        OAuthToken.status == TokenStatus.active,
    ).update({"status": TokenStatus.revoked})

    # Store new token
    oauth_token = OAuthToken(
        provider=OAuthProvider.zoom,
        account_email=account_email,
        scopes=token_data.get("scope", ""),
        access_token_enc=encryptor.encrypt(access_token),
        refresh_token_enc=encryptor.encrypt(token_data.get("refresh_token", ""))
        if token_data.get("refresh_token")
        else None,
        expires_at=expires_at,
        status=TokenStatus.active,
    )
    db.add(oauth_token)
    db.commit()

    logger.info(
        "Zoom OAuth completed successfully",
        email=account_email,
        token_id=str(oauth_token.id),
    )

    # Redirect to frontend with success message
    frontend_url = settings.oauth_redirect_base_url.replace(":8000", ":3000")
    return {
        "message": "Zoom integration connected successfully!",
        "account_email": account_email,
        "redirect_url": f"{frontend_url}/integrations?status=success&provider=zoom",
    }


@router.delete("/integrations/zoom/disconnect")
async def disconnect_zoom(db: Session = Depends(get_db)):
    """
    Disconnect Zoom integration.

    Args:
        db: Database session

    Returns:
        Success message
    """
    # Revoke all active Zoom tokens
    updated = (
        db.query(OAuthToken)
        .filter(
            OAuthToken.provider == OAuthProvider.zoom,
            OAuthToken.status == TokenStatus.active,
        )
        .update({"status": TokenStatus.revoked})
    )
    db.commit()

    logger.info("Zoom integration disconnected", tokens_revoked=updated)

    return {"message": "Zoom integration disconnected successfully"}


@router.post("/integrations/zoom/sync")
async def sync_zoom(
    days_back: int = Query(default=30, description="Number of days back to fetch recordings"),
    db: Session = Depends(get_db),
):
    """
    Manually trigger Zoom recordings sync.

    Args:
        days_back: Number of days back to fetch recordings
        db: Database session

    Returns:
        Sync statistics
    """
    from apps.api.services.zoom_client import sync_zoom_recordings

    logger.info("Starting manual Zoom sync", days_back=days_back)

    stats = await sync_zoom_recordings(db, days_back=days_back)

    if "error" in stats:
        raise HTTPException(status_code=400, detail=stats["error"])

    return {
        "message": "Zoom sync completed",
        "stats": stats,
    }


@router.get("/integrations/google/authorize", response_model=OAuthAuthorizeResponse)
async def authorize_google():
    """
    Start Google OAuth flow.

    Returns:
        Authorization URL to redirect user to
    """
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )

    # Generate random state for CSRF protection
    state = secrets.token_urlsafe(32)

    # Store state in memory (use Redis in production)
    _oauth_states[state] = {
        "provider": "google",
        "created_at": datetime.utcnow(),
    }

    # Build authorization URL
    redirect_uri = f"{settings.oauth_redirect_base_url}/auth/google/callback"
    params = {
        "response_type": "code",
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": " ".join([
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/documents.readonly",
            "https://www.googleapis.com/auth/userinfo.email",
        ]),
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    logger.info("Starting Google OAuth flow", state=state, redirect_uri=redirect_uri)

    return OAuthAuthorizeResponse(authorization_url=auth_url, state=state)


@router.delete("/integrations/google/disconnect")
async def disconnect_google(db: Session = Depends(get_db)):
    """
    Disconnect Google integration.

    Args:
        db: Database session

    Returns:
        Success message
    """
    # Revoke all active Google tokens
    updated = (
        db.query(OAuthToken)
        .filter(
            OAuthToken.provider == OAuthProvider.google,
            OAuthToken.status == TokenStatus.active,
        )
        .update({"status": TokenStatus.revoked})
    )
    db.commit()

    logger.info("Google integration disconnected", tokens_revoked=updated)

    return {"message": "Google integration disconnected successfully"}


@router.post("/integrations/google/sync")
async def sync_google(
    folder_ids: str = Query(default="", description="Comma-separated Google Drive folder IDs"),
    db: Session = Depends(get_db),
):
    """
    Manually trigger Google Drive documents sync.

    Args:
        folder_ids: Comma-separated folder IDs to sync from
        db: Database session

    Returns:
        Sync statistics
    """
    from apps.api.services.google_client import sync_google_docs

    logger.info("Starting manual Google Drive sync", folder_ids=folder_ids)

    folder_id_list = [fid.strip() for fid in folder_ids.split(",") if fid.strip()]
    stats = await sync_google_docs(db, folder_ids=folder_id_list)

    if "error" in stats:
        raise HTTPException(status_code=400, detail=stats["error"])

    return {
        "message": "Google Drive sync completed",
        "stats": stats,
    }
