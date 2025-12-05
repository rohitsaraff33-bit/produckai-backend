"""Zoom OAuth provider."""

from typing import List
from apps.api.auth.providers.base import OAuthProvider


class ZoomOAuthProvider(OAuthProvider):
    """Zoom OAuth 2.0 provider with Cloud Recordings scope."""

    @property
    def authorization_endpoint(self) -> str:
        return "https://zoom.us/oauth/authorize"

    @property
    def token_endpoint(self) -> str:
        return "https://zoom.us/oauth/token"

    def get_default_scopes(self) -> List[str]:
        return [
            "cloud_recording:read:recording",
            "cloud_recording:read:meeting_transcript",
        ]
