"""Token encryption and secret management using AES-GCM."""

import base64
import os
from typing import Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from apps.api.config import get_settings

settings = get_settings()


class SecretsManager:
    """Manages encryption/decryption of sensitive data like OAuth tokens."""

    def __init__(self):
        """Initialize with APP_SECRET from environment."""
        app_secret = getattr(settings, 'app_secret', None)

        if not app_secret:
            raise ValueError(
                "APP_SECRET not configured. Generate with: "
                "python -c 'import os,base64; print(base64.b64encode(os.urandom(32)).decode())'"
            )

        # Decode base64 secret to bytes
        try:
            self.key = base64.b64decode(app_secret)
        except Exception as e:
            raise ValueError(f"Invalid APP_SECRET format (expected base64): {e}")

        if len(self.key) != 32:
            raise ValueError("APP_SECRET must be 32 bytes (256 bits) when decoded")

        self.aesgcm = AESGCM(self.key)

    def encrypt(self, plaintext: str) -> Tuple[str, str]:
        """Encrypt plaintext string.

        Args:
            plaintext: String to encrypt

        Returns:
            Tuple of (nonce_b64, ciphertext_b64)
        """
        if not plaintext:
            return "", ""

        # Generate random nonce (96 bits recommended for GCM)
        nonce = os.urandom(12)

        # Encrypt
        ciphertext = self.aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)

        # Return base64-encoded nonce and ciphertext
        return (base64.b64encode(nonce).decode('ascii'), base64.b64encode(ciphertext).decode('ascii'))

    def decrypt(self, nonce_b64: str, ciphertext_b64: str) -> str:
        """Decrypt ciphertext.

        Args:
            nonce_b64: Base64-encoded nonce
            ciphertext_b64: Base64-encoded ciphertext

        Returns:
            Decrypted plaintext string

        Raises:
            ValueError: If decryption fails
        """
        if not nonce_b64 or not ciphertext_b64:
            return ""

        try:
            nonce = base64.b64decode(nonce_b64)
            ciphertext = base64.b64decode(ciphertext_b64)

            plaintext_bytes = self.aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext_bytes.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")


# Singleton instance
_secrets_manager: SecretsManager | None = None


def get_secrets_manager() -> SecretsManager:
    """Get secrets manager singleton."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager
