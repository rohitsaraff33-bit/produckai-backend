"""Celery scheduled task for proactive token refresh."""

import logging
from datetime import datetime, timedelta

from apps.api.core.secrets import get_secrets_manager
from apps.api.database import get_db_context
from apps.api.models.oauth import OAuthToken, TokenStatus
from apps.api.auth.providers import GoogleOAuthProvider, ZoomOAuthProvider
from apps.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="refresh_expiring_tokens")
def refresh_expiring_tokens():
    """Refresh tokens expiring in the next 30 minutes."""
    with get_db_context() as db:
        # Find tokens expiring soon
        threshold = datetime.utcnow() + timedelta(minutes=30)

        tokens = (
            db.query(OAuthToken)
            .filter(
                OAuthToken.status == TokenStatus.active,
                OAuthToken.expires_at < threshold,
                OAuthToken.refresh_token_enc.isnot(None),
            )
            .all()
        )

        logger.info(f"Found {len(tokens)} tokens to refresh")

        secrets_mgr = get_secrets_manager()
        refreshed = 0
        failed = 0

        for token in tokens:
            try:
                # Decrypt refresh token
                nonce, ct = token.refresh_token_enc.split('|')
                refresh_token = secrets_mgr.decrypt(nonce, ct)

                # Get provider
                if token.provider.value == 'google':
                    provider = GoogleOAuthProvider('', '', '')  # Client creds from env
                elif token.provider.value == 'zoom':
                    provider = ZoomOAuthProvider('', '', '')
                else:
                    continue

                # Refresh
                import asyncio

                new_tokens = asyncio.run(provider.refresh_access_token(refresh_token))

                # Encrypt new access token
                access_nonce, access_ct = secrets_mgr.encrypt(new_tokens['access_token'])
                token.access_token_enc = f"{access_nonce}|{access_ct}"

                # Update refresh token if provider returned new one
                if 'refresh_token' in new_tokens:
                    refresh_nonce, refresh_ct = secrets_mgr.encrypt(new_tokens['refresh_token'])
                    token.refresh_token_enc = f"{refresh_nonce}|{refresh_ct}"

                # Update expiry
                token.expires_at = datetime.utcnow() + timedelta(seconds=new_tokens['expires_in'])
                token.updated_at = datetime.utcnow()

                refreshed += 1

            except Exception as e:
                logger.error(f"Failed to refresh token {token.id}: {e}")
                token.status = TokenStatus.expired
                failed += 1

        db.commit()
        logger.info(f"Token refresh complete: {refreshed} refreshed, {failed} failed")

        return {"refreshed": refreshed, "failed": failed}
