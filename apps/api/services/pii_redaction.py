"""PII redaction service - removes sensitive information from text before processing."""

import re
from typing import Optional

from apps.api.config import get_settings

settings = get_settings()


class PIIRedactionService:
    """Service for redacting PII from text."""

    # Regex patterns for PII detection
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    PHONE_PATTERN = re.compile(
        r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b'
    )
    URL_PATTERN = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    # Credit card pattern (basic - matches common formats)
    CREDIT_CARD_PATTERN = re.compile(r'\b(?:\d[ -]*?){13,19}\b')
    # SSN pattern (US)
    SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')

    def __init__(self, enabled: Optional[bool] = None):
        """Initialize PII redaction service.

        Args:
            enabled: Override for PII redaction enabled setting. If None, uses env setting.
        """
        self.enabled = (
            enabled if enabled is not None else getattr(settings, 'pii_redaction_enabled', True)
        )

    def redact(self, text: str) -> str:
        """Redact PII from text.

        Args:
            text: Input text to redact

        Returns:
            Text with PII replaced by placeholders
        """
        if not self.enabled:
            return text

        redacted = text

        # Redact emails
        redacted = self.EMAIL_PATTERN.sub('[EMAIL]', redacted)

        # Redact phone numbers
        redacted = self.PHONE_PATTERN.sub('[PHONE]', redacted)

        # Redact URLs (but preserve domain for context if it's not in a sensitive context)
        # For now, we'll redact fully
        redacted = self.URL_PATTERN.sub('[URL]', redacted)

        # Redact credit cards
        redacted = self.CREDIT_CARD_PATTERN.sub('[CREDIT_CARD]', redacted)

        # Redact SSNs
        redacted = self.SSN_PATTERN.sub('[SSN]', redacted)

        return redacted

    def redact_batch(self, texts: list[str]) -> list[str]:
        """Redact PII from a batch of texts.

        Args:
            texts: List of input texts

        Returns:
            List of texts with PII redacted
        """
        return [self.redact(text) for text in texts]


def get_pii_redaction_service() -> PIIRedactionService:
    """Get PII redaction service instance."""
    return PIIRedactionService()
