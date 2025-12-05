"""Base OAuth provider with PKCE support."""

import hashlib
import base64
import secrets
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import httpx


class OAuthProvider(ABC):
    """Base class for OAuth 2.0 providers with PKCE."""

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    @property
    @abstractmethod
    def authorization_endpoint(self) -> str:
        """OAuth authorization URL."""
        pass

    @property
    @abstractmethod
    def token_endpoint(self) -> str:
        """OAuth token exchange URL."""
        pass

    @abstractmethod
    def get_default_scopes(self) -> List[str]:
        """Default scopes for this provider."""
        pass

    def generate_pkce_pair(self) -> Dict[str, str]:
        """Generate PKCE code verifier and challenge.

        Returns:
            Dict with 'code_verifier' and 'code_challenge'
        """
        # Generate code verifier (43-128 characters)
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

        # Generate code challenge (S256)
        challenge_bytes = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8').rstrip('=')

        return {
            'code_verifier': code_verifier,
            'code_challenge': code_challenge,
        }

    def get_additional_auth_params(self) -> Dict[str, str]:
        """Get provider-specific authorization parameters.

        Override this method to add provider-specific parameters.
        """
        return {}

    def get_authorization_url(
        self, state: str, code_challenge: str, scopes: Optional[List[str]] = None
    ) -> str:
        """Build authorization URL with PKCE.

        Args:
            state: CSRF state token
            code_challenge: PKCE code challenge (S256)
            scopes: List of OAuth scopes

        Returns:
            Full authorization URL
        """
        scopes = scopes or self.get_default_scopes()
        scope_str = ' '.join(scopes)

        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': scope_str,
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
        }

        # Add provider-specific parameters
        params.update(self.get_additional_auth_params())

        # Use httpx.QueryParams to properly encode the query string
        query_params = httpx.QueryParams(params)
        return f"{self.authorization_endpoint}?{query_params}"

    async def exchange_code(self, code: str, code_verifier: str) -> Dict:
        """Exchange authorization code for tokens.

        Args:
            code: Authorization code from callback
            code_verifier: PKCE code verifier

        Returns:
            Dict with access_token, refresh_token, expires_in, scope
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_endpoint,
                data={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'code': code,
                    'code_verifier': code_verifier,
                    'redirect_uri': self.redirect_uri,
                    'grant_type': 'authorization_code',
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
            )
            response.raise_for_status()
            data = response.json()

            return {
                'access_token': data['access_token'],
                'refresh_token': data.get('refresh_token'),
                'expires_in': data.get('expires_in', 3600),
                'scope': data.get('scope', ''),
            }

    async def refresh_access_token(self, refresh_token: str) -> Dict:
        """Refresh access token using refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            Dict with new access_token, expires_in
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_endpoint,
                data={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'refresh_token': refresh_token,
                    'grant_type': 'refresh_token',
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
            )
            response.raise_for_status()
            data = response.json()

            return {
                'access_token': data['access_token'],
                'expires_in': data.get('expires_in', 3600),
                'refresh_token': data.get('refresh_token', refresh_token),
            }
