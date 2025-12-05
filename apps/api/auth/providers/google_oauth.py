"""Google OAuth provider."""

from typing import Dict, List
from apps.api.auth.providers.base import OAuthProvider


class GoogleOAuthProvider(OAuthProvider):
    """Google OAuth 2.0 provider with Drive and Docs scopes."""

    @property
    def authorization_endpoint(self) -> str:
        return "https://accounts.google.com/o/oauth2/v2/auth"

    @property
    def token_endpoint(self) -> str:
        return "https://oauth2.googleapis.com/token"

    def get_default_scopes(self) -> List[str]:
        return [
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/documents.readonly",
            "https://www.googleapis.com/auth/userinfo.email",
        ]

    def get_additional_auth_params(self) -> Dict[str, str]:
        """Google-specific authorization parameters."""
        return {
            'access_type': 'offline',  # Request refresh token
        }
