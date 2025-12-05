"""OAuth providers for Google and Zoom."""

from apps.api.auth.providers.google_oauth import GoogleOAuthProvider
from apps.api.auth.providers.zoom_oauth import ZoomOAuthProvider

__all__ = ["GoogleOAuthProvider", "ZoomOAuthProvider"]
