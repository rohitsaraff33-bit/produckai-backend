"""Slack message content extractor."""

from datetime import datetime

from apps.api.services.ingestion.base import (
    ContentChunk,
    ContentExtractor,
    CustomerInfo,
)


class SlackExtractor(ContentExtractor):
    """
    Extract customer and feedback from Slack messages.

    Slack messages are typically short and don't need chunking.
    Customer is derived from channel name or user metadata.
    """

    def extract_customer(self, raw_content: dict) -> CustomerInfo:
        """
        Extract customer from Slack message metadata.

        Uses channel name or user profile information.

        Args:
            raw_content: Dict with 'channel_name', 'user', 'text', etc.

        Returns:
            CustomerInfo with extracted name and confidence
        """
        self.validate_content(raw_content)

        # Strategy 1: Check if channel name indicates customer
        # e.g., "customer-acme-corp", "support-techflow"
        channel_name = raw_content.get("channel_name", "")
        if channel_name:
            parts = channel_name.lower().split("-")
            if "customer" in parts or "support" in parts:
                # Find customer part
                customer_parts = [p for p in parts if p not in ["customer", "support", "general"]]
                if customer_parts:
                    customer = " ".join(customer_parts).title()
                    return CustomerInfo(
                        name=customer,
                        confidence=0.7,
                        extraction_method="channel_name",
                        metadata={"channel": channel_name}
                    )

        # Strategy 2: Use default "Demo" for internal channels
        # TODO: Add user profile lookup to get actual customer
        return CustomerInfo(
            name="Demo",
            confidence=0.5,
            extraction_method="fallback_demo",
            metadata={"channel": channel_name}
        )

    def should_chunk(self, raw_content: dict) -> bool:
        """
        Slack messages are typically short and don't need chunking.

        Only chunk if message is unusually long (e.g., shared document).
        """
        text = raw_content.get("text", "")
        return len(text) > 2000  # Very generous threshold

    def chunk_content(self, raw_content: dict) -> list[ContentChunk]:
        """
        Chunk Slack message content.

        Most Slack messages are single chunks.

        Args:
            raw_content: Dict with 'text', 'user', 'channel', 'ts', etc.

        Returns:
            List of ContentChunk objects (typically just one)
        """
        self.validate_content(raw_content)

        text = raw_content.get("text", "")
        message_ts = raw_content.get("ts", "unknown")
        channel = raw_content.get("channel_name", "unknown")
        user = raw_content.get("user_name", "unknown")

        return [
            ContentChunk(
                id=f"slack_{channel}_{message_ts}",
                text=text,
                metadata={
                    "channel": channel,
                    "user": user,
                    "thread_ts": raw_content.get("thread_ts"),
                    "timestamp": message_ts,
                    "created_at": raw_content.get("created_at", datetime.utcnow()),
                }
            )
        ]

    def validate_content(self, raw_content: dict) -> None:
        """Validate Slack content structure."""
        super().validate_content(raw_content)

        if "text" not in raw_content:
            raise ValueError("Slack content must have 'text' field")
