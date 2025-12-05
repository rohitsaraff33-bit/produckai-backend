"""OAuth authentication endpoints."""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.auth.providers import GoogleOAuthProvider, ZoomOAuthProvider
from apps.api.config import get_settings
from apps.api.core.secrets import get_secrets_manager
from apps.api.database import get_db
from apps.api.models.oauth import OAuthProvider, OAuthToken, TokenStatus

router = APIRouter()
settings = get_settings()


class ConnectionInfo(BaseModel):
    """OAuth connection info."""

    provider: str
    account_email: Optional[str]
    scopes: str
    expires_at: str
    expires_in_seconds: int
    status: str


class ConnectionsResponse(BaseModel):
    """List of OAuth connections."""

    connections: list[ConnectionInfo]


# In-memory state storage (use Redis in production)
_oauth_states = {}


def get_provider(provider_name: str):
    """Get OAuth provider instance."""
    base_url = getattr(settings, 'oauth_redirect_base_url', 'http://localhost:8000')

    if provider_name == 'google':
        return GoogleOAuthProvider(
            client_id=getattr(settings, 'google_client_id', ''),
            client_secret=getattr(settings, 'google_client_secret', ''),
            redirect_uri=f"{base_url}/auth/google/callback",
        )
    elif provider_name == 'zoom':
        return ZoomOAuthProvider(
            client_id=getattr(settings, 'zoom_client_id', ''),
            client_secret=getattr(settings, 'zoom_client_secret', ''),
            redirect_uri=f"{base_url}/auth/zoom/callback",
        )
    else:
        raise ValueError(f"Unknown provider: {provider_name}")


@router.get("/google/start")
async def google_oauth_start():
    """Start Google OAuth flow."""
    provider = get_provider('google')
    pkce_pair = provider.generate_pkce_pair()
    state = secrets.token_urlsafe(32)

    # Store state and code_verifier (use Redis in production)
    _oauth_states[state] = {
        'provider': 'google',
        'code_verifier': pkce_pair['code_verifier'],
        'created_at': datetime.utcnow(),
    }

    auth_url = provider.get_authorization_url(state, pkce_pair['code_challenge'])
    return {"authorization_url": auth_url, "state": state}


@router.get("/google/callback")
async def google_oauth_callback(
    code: str = Query(...), state: str = Query(...), db: Session = Depends(get_db)
):
    """Handle Google OAuth callback."""
    # Validate state
    state_data = _oauth_states.get(state)
    if not state_data:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    # Exchange code for tokens
    provider = get_provider('google')
    tokens = await provider.exchange_code(code, state_data['code_verifier'])

    # Clean up state
    del _oauth_states[state]

    # Fetch user email from userinfo endpoint
    import httpx
    account_email = None
    try:
        async with httpx.AsyncClient() as client:
            userinfo_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
            )
            userinfo_response.raise_for_status()
            userinfo = userinfo_response.json()
            account_email = userinfo.get("email", "")
    except Exception as e:
        # Log but don't fail if userinfo fetch fails
        pass

    # Encrypt and store tokens
    secrets_mgr = get_secrets_manager()
    access_nonce, access_ct = secrets_mgr.encrypt(tokens['access_token'])
    refresh_nonce, refresh_ct = secrets_mgr.encrypt(tokens.get('refresh_token', ''))

    expires_at = datetime.utcnow() + timedelta(seconds=tokens['expires_in'])

    # Revoke any existing active tokens for this provider
    db.query(OAuthToken).filter(
        OAuthToken.provider == OAuthProvider.google,
        OAuthToken.status == TokenStatus.active,
    ).update({"status": TokenStatus.revoked})

    # Save to database
    oauth_token = OAuthToken(
        provider=OAuthProvider.google,
        account_email=account_email,
        scopes=tokens['scope'],
        access_token_enc=f"{access_nonce}|{access_ct}",
        refresh_token_enc=f"{refresh_nonce}|{refresh_ct}" if refresh_ct else None,
        expires_at=expires_at,
        status=TokenStatus.active,
    )
    db.add(oauth_token)
    db.commit()

    # Redirect to frontend with success message
    frontend_url = settings.oauth_redirect_base_url.replace(":8000", ":3000")
    return {
        "status": "success",
        "provider": "google",
        "account_email": account_email,
        "expires_at": expires_at.isoformat(),
        "redirect_url": f"{frontend_url}/integrations?status=success&provider=google",
        "message": "Google account connected successfully!",
    }


@router.get("/zoom/start")
async def zoom_oauth_start():
    """Start Zoom OAuth flow."""
    provider = get_provider('zoom')
    pkce_pair = provider.generate_pkce_pair()
    state = secrets.token_urlsafe(32)

    _oauth_states[state] = {
        'provider': 'zoom',
        'code_verifier': pkce_pair['code_verifier'],
        'created_at': datetime.utcnow(),
    }

    auth_url = provider.get_authorization_url(state, pkce_pair['code_challenge'])
    return {"authorization_url": auth_url, "state": state}


@router.get("/zoom/callback")
async def zoom_oauth_callback(
    code: str = Query(...), state: str = Query(...), db: Session = Depends(get_db)
):
    """Handle Zoom OAuth callback."""
    state_data = _oauth_states.get(state)
    if not state_data:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    provider = get_provider('zoom')
    tokens = await provider.exchange_code(code, state_data['code_verifier'])

    del _oauth_states[state]

    secrets_mgr = get_secrets_manager()
    access_nonce, access_ct = secrets_mgr.encrypt(tokens['access_token'])
    refresh_nonce, refresh_ct = secrets_mgr.encrypt(tokens.get('refresh_token', ''))

    expires_at = datetime.utcnow() + timedelta(seconds=tokens['expires_in'])

    oauth_token = OAuthToken(
        provider=OAuthProvider.zoom,
        account_email=None,
        scopes=tokens['scope'],
        access_token_enc=f"{access_nonce}|{access_ct}",
        refresh_token_enc=f"{refresh_nonce}|{refresh_ct}" if refresh_ct else None,
        expires_at=expires_at,
        status=TokenStatus.active,
    )
    db.add(oauth_token)
    db.commit()

    return {
        "status": "success",
        "provider": "zoom",
        "expires_at": expires_at.isoformat(),
        "message": "Zoom account connected successfully. You can close this window.",
    }


@router.get("/connections", response_model=ConnectionsResponse)
async def get_connections(db: Session = Depends(get_db)):
    """Get list of active OAuth connections."""
    tokens = (
        db.query(OAuthToken)
        .filter(OAuthToken.status == TokenStatus.active)
        .order_by(OAuthToken.created_at.desc())
        .all()
    )

    connections = []
    now = datetime.utcnow()

    for token in tokens:
        expires_in = (token.expires_at - now).total_seconds()
        connections.append(
            ConnectionInfo(
                provider=token.provider.value,
                account_email=token.account_email,
                scopes=token.scopes,
                expires_at=token.expires_at.isoformat(),
                expires_in_seconds=int(max(0, expires_in)),
                status=token.status.value,
            )
        )

    return ConnectionsResponse(connections=connections)


@router.post("/{provider}/disconnect")
async def disconnect_provider(provider: str, db: Session = Depends(get_db)):
    """Disconnect OAuth provider."""
    if provider not in ['google', 'zoom']:
        raise HTTPException(status_code=400, detail="Invalid provider")

    # Mark all tokens as revoked
    db.query(OAuthToken).filter(
        OAuthToken.provider == provider, OAuthToken.status == TokenStatus.active
    ).update({OAuthToken.status: TokenStatus.revoked})

    db.commit()

    return {"status": "success", "message": f"{provider.capitalize()} disconnected"}
