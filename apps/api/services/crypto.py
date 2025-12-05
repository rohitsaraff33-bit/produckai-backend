"""Cryptography utilities for secure token storage."""

import os
from base64 import b64decode, b64encode

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class TokenEncryption:
    """Handles encryption and decryption of OAuth tokens using AES-GCM."""

    def __init__(self, encryption_key: str):
        """
        Initialize with encryption key.

        Args:
            encryption_key: Base64-encoded 256-bit key (32 bytes)
        """
        self.key = b64decode(encryption_key)
        if len(self.key) != 32:
            raise ValueError("Encryption key must be 32 bytes (256 bits)")
        self.cipher = AESGCM(self.key)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a token string.

        Args:
            plaintext: Token to encrypt

        Returns:
            Base64-encoded "nonce|ciphertext" string
        """
        if not plaintext:
            raise ValueError("Cannot encrypt empty string")

        # Generate random nonce
        nonce = os.urandom(12)

        # Encrypt
        ciphertext = self.cipher.encrypt(nonce, plaintext.encode("utf-8"), None)

        # Return as "nonce|ciphertext" base64
        combined = nonce + ciphertext
        return b64encode(combined).decode("utf-8")

    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt a token string.

        Args:
            encrypted: Base64-encoded "nonce|ciphertext" string

        Returns:
            Decrypted plaintext token

        Raises:
            ValueError: If decryption fails
        """
        if not encrypted:
            raise ValueError("Cannot decrypt empty string")

        try:
            # Decode from base64
            combined = b64decode(encrypted)

            # Split nonce and ciphertext
            nonce = combined[:12]
            ciphertext = combined[12:]

            # Decrypt
            plaintext = self.cipher.decrypt(nonce, ciphertext, None)
            return plaintext.decode("utf-8")
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")


def get_token_encryptor() -> TokenEncryption:
    """Get token encryptor instance using environment key."""
    from apps.api.config import get_settings

    settings = get_settings()
    return TokenEncryption(settings.encryption_key)
