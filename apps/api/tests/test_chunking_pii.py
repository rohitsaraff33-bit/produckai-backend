"""Tests for chunking and PII redaction services."""

import pytest
from apps.api.services.chunking import ChunkingService, get_chunking_service
from apps.api.services.pii_redaction import PIIRedactionService


class TestChunkingService:
    """Test chunking service functionality."""

    def test_chunk_short_text(self):
        """Test chunking short text that doesn't need splitting."""
        service = get_chunking_service(chunk_size=500, overlap=50)
        text = "This is a short text."

        chunks = service.chunk_text(text)

        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].chunk_idx == 0

    def test_chunk_long_text(self):
        """Test chunking long text into multiple chunks."""
        service = get_chunking_service(chunk_size=50, overlap=10)  # Small chunks for testing
        text = " ".join(["This is a sentence." for _ in range(50)])  # ~1000 chars

        chunks = service.chunk_text(text)

        # Should create multiple chunks
        assert len(chunks) > 1

        # Check chunk indices
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_idx == i

    def test_chunk_with_headers(self):
        """Test chunking markdown text with headers."""
        service = get_chunking_service(chunk_size=200, overlap=20, split_on_headers=True)
        text = """# Heading 1
Content under heading 1.

## Heading 2
Content under heading 2.

### Heading 3
More content here.
"""

        chunks = service.chunk_text(text)

        # Should split by headers
        assert len(chunks) >= 1

        # Check metadata includes header levels
        for chunk in chunks:
            assert 'header_level' in chunk.metadata

    def test_chunk_empty_text(self):
        """Test chunking empty text."""
        service = get_chunking_service()
        text = ""

        chunks = service.chunk_text(text)

        assert len(chunks) == 0


class TestPIIRedaction:
    """Test PII redaction service."""

    def test_redact_email(self):
        """Test email redaction."""
        service = PIIRedactionService(enabled=True)
        text = "Contact me at john.doe@example.com for more info."

        redacted = service.redact(text)

        assert "[EMAIL]" in redacted
        assert "john.doe@example.com" not in redacted

    def test_redact_phone(self):
        """Test phone number redaction."""
        service = PIIRedactionService(enabled=True)
        text = "Call me at (555) 123-4567 or 555-987-6543."

        redacted = service.redact(text)

        assert "[PHONE]" in redacted
        assert "555" not in redacted or redacted.count("555") < 2

    def test_redact_url(self):
        """Test URL redaction."""
        service = PIIRedactionService(enabled=True)
        text = "Visit our site at https://example.com/secret-page for details."

        redacted = service.redact(text)

        assert "[URL]" in redacted
        assert "https://example.com" not in redacted

    def test_redact_ssn(self):
        """Test SSN redaction."""
        service = PIIRedactionService(enabled=True)
        text = "My SSN is 123-45-6789."

        redacted = service.redact(text)

        assert "[SSN]" in redacted
        assert "123-45-6789" not in redacted

    def test_redact_disabled(self):
        """Test that redaction can be disabled."""
        service = PIIRedactionService(enabled=False)
        text = "Email: test@example.com, Phone: (555) 123-4567"

        redacted = service.redact(text)

        # Should not redact when disabled
        assert text == redacted

    def test_redact_batch(self):
        """Test batch redaction."""
        service = PIIRedactionService(enabled=True)
        texts = [
            "Email me at alice@example.com",
            "Call bob at (555) 111-2222",
            "Visit https://secret.com",
        ]

        redacted_texts = service.redact_batch(texts)

        assert len(redacted_texts) == 3
        assert "[EMAIL]" in redacted_texts[0]
        assert "[PHONE]" in redacted_texts[1]
        assert "[URL]" in redacted_texts[2]
