"""Zoom transcript content extractor."""

from datetime import datetime

from apps.api.services.ingestion.base import (
    ContentChunk,
    ContentExtractor,
    CustomerInfo,
)


class ZoomExtractor(ContentExtractor):
    """
    Extract customer and feedback from Zoom transcripts.

    Zoom transcripts are similar to Google Drive transcripts in VTT format.
    This extractor uses similar logic to GDrive for transcript chunking.
    """

    def extract_customer(self, raw_content: dict) -> CustomerInfo:
        """
        Extract customer from Zoom meeting data.

        For now, uses a simple approach:
        1. Check meeting metadata for customer name
        2. Fallback to "Unknown"

        TODO: Implement transcript-based extraction similar to GDrive

        Args:
            raw_content: Dict with 'topic', 'host_email', 'transcript', etc.

        Returns:
            CustomerInfo with extracted name and confidence
        """
        self.validate_content(raw_content)

        # Strategy 1: Get from meeting topic if it contains customer name
        topic = raw_content.get("topic", "")
        if topic and "-" in topic:
            # Assume format like "Customer Call - Acme Corp"
            parts = topic.split("-")
            if len(parts) > 1:
                potential_customer = parts[1].strip()
                if potential_customer:
                    return CustomerInfo(
                        name=potential_customer,
                        confidence=0.6,
                        extraction_method="meeting_topic",
                        metadata={"topic": topic}
                    )

        # Strategy 2: Use host email prefix as fallback
        host_email = raw_content.get("host_email", "")
        if host_email and "@" in host_email:
            return CustomerInfo(
                name=host_email.split("@")[0],
                confidence=0.3,
                extraction_method="fallback_host",
                metadata={"host_email": host_email}
            )

        # Last resort
        return CustomerInfo(
            name="Unknown",
            confidence=0.1,
            extraction_method="fallback_unknown"
        )

    def should_chunk(self, raw_content: dict) -> bool:
        """
        Zoom transcripts are typically long and should be chunked.

        Args:
            raw_content: Dict with transcript data

        Returns:
            True if transcript exists and is substantial
        """
        transcript = raw_content.get("transcript", "")
        return len(transcript) > 1000  # Simple length-based check

    def chunk_content(self, raw_content: dict) -> list[ContentChunk]:
        """
        Chunk Zoom transcript into feedback items.

        For now, returns whole transcript as single chunk.
        TODO: Implement VTT parsing similar to GDrive extractor

        Args:
            raw_content: Dict with 'transcript', 'meeting_id', 'topic', etc.

        Returns:
            List of ContentChunk objects
        """
        self.validate_content(raw_content)

        transcript = raw_content.get("transcript", "")
        meeting_id = raw_content.get("meeting_id", "unknown")
        topic = raw_content.get("topic", "Zoom Meeting")

        # Simple approach: return whole transcript
        # TODO: Parse VTT format and chunk by speaker like GDrive
        return [
            ContentChunk(
                id=meeting_id,
                text=transcript,
                metadata={
                    "topic": topic,
                    "host_email": raw_content.get("host_email"),
                    "started_at": raw_content.get("started_at"),
                    "ended_at": raw_content.get("ended_at"),
                    "duration": raw_content.get("duration"),
                    "created_at": raw_content.get("created_at", datetime.utcnow()),
                }
            )
        ]

    def validate_content(self, raw_content: dict) -> None:
        """Validate Zoom content structure."""
        super().validate_content(raw_content)

        if "transcript" not in raw_content:
            raise ValueError("Zoom content must have 'transcript' field")
