"""Google Drive content extractor."""

import re
from datetime import datetime

from apps.api.services.ingestion.base import (
    ContentChunk,
    ContentExtractor,
    CustomerInfo,
    FEEDBACK_KEYWORDS,
)


class GDriveExtractor(ContentExtractor):
    """Extract customer and feedback from Google Drive documents."""

    # Minimum content length to consider chunking (characters)
    CHUNKING_THRESHOLD = 2000

    # Maximum chunk size for transcripts (characters)
    MAX_CHUNK_SIZE = 500

    def extract_customer(self, raw_content: dict) -> CustomerInfo:
        """
        Extract customer name from Google Drive document.

        Tries multiple strategies in order of reliability:
        1. Structured metadata (if available)
        2. Pattern matching in content
        3. Fallback to owner name

        Args:
            raw_content: Dict with 'text', 'title', 'owner', etc.

        Returns:
            CustomerInfo with extracted name and confidence
        """
        self.validate_content(raw_content)

        text = raw_content.get("text", "")

        # Strategy 1: Pattern matching for customer mentions
        customer = self._extract_from_patterns(text)
        if customer:
            return CustomerInfo(
                name=customer,
                confidence=0.8,
                extraction_method="regex_pattern",
                metadata={"pattern_matched": True},
            )

        # Strategy 2: Extract from participant info (for transcripts)
        customer = self._extract_from_participants(text)
        if customer:
            return CustomerInfo(
                name=customer,
                confidence=0.7,
                extraction_method="regex_participant",
                metadata={"from_participant": True},
            )

        # Strategy 3: Fallback to owner name (low confidence)
        owner = raw_content.get("owner", "")
        if owner and "@" in owner:
            fallback_name = owner.split("@")[0]
            return CustomerInfo(
                name=fallback_name,
                confidence=0.3,
                extraction_method="fallback_owner",
                metadata={"owner_email": owner},
            )

        # Last resort: Unknown
        return CustomerInfo(
            name="Unknown", confidence=0.1, extraction_method="fallback_unknown"
        )

    def _extract_from_patterns(self, text: str) -> str | None:
        """Extract customer using common patterns in text."""
        # Pattern 1: "their customer [Customer Name]"
        match = re.search(
            r"(?:their customer|customer)\s+([A-Z][A-Za-z\s&]+?)(?:\s+to capture|\s+on|\.)",
            text,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()

        return None

    def _extract_from_participants(self, text: str) -> str | None:
        """Extract customer from participant information."""
        # Pattern: "Participants: ... (Company - Title)"
        match = re.search(
            r"Participants:.*?\(([A-Z][A-Za-z\s&]+?)\s+-\s+", text, re.IGNORECASE | re.DOTALL
        )
        if match:
            company = match.group(1).strip()
            # Filter out our own company
            if company not in ["PulseDrive", "Product"]:
                return company

        return None

    def should_chunk(self, raw_content: dict) -> bool:
        """
        Determine if content should be chunked.

        Chunk if:
        - Content is longer than threshold
        - Content appears to be a transcript (has timestamps)
        """
        text = raw_content.get("text", "")

        # Check length
        if len(text) < self.CHUNKING_THRESHOLD:
            return False

        # Check if it's a transcript (has VTT timestamps)
        has_timestamps = bool(re.search(r"\d{2}:\d{2}:\d{2}\.\d{3}\s+-->", text))

        return has_timestamps

    def chunk_content(self, raw_content: dict) -> list[ContentChunk]:
        """
        Chunk Google Drive content into feedback items.

        For transcripts: Extract individual statements with feedback keywords
        For documents: Return as single chunk (or implement doc-specific chunking)

        Args:
            raw_content: Dict with 'text', 'title', 'source_id', etc.

        Returns:
            List of ContentChunk objects
        """
        self.validate_content(raw_content)

        text = raw_content.get("text", "")
        source_id = raw_content.get("source_id", "unknown")
        title = raw_content.get("title", "Untitled")

        # Prepare metadata with JSON-serializable values
        created_at = raw_content.get("created_at")
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        elif created_at is None:
            created_at = datetime.utcnow().isoformat()

        # Check if we should chunk
        if not self.should_chunk(raw_content):
            # Return as single chunk
            return [
                ContentChunk(
                    id=source_id,
                    text=text,
                    metadata={
                        "title": title,
                        "url": raw_content.get("url"),
                        "modified_time": raw_content.get("modified_time"),
                        "owner": raw_content.get("owner"),
                        "created_at": created_at,
                    },
                )
            ]

        # Chunk transcript by speaker statements
        chunks = self._chunk_transcript(text, source_id, title, raw_content)

        return chunks if chunks else [
            ContentChunk(
                id=source_id,
                text=text,
                metadata={
                    "title": title,
                    "url": raw_content.get("url"),
                    "created_at": created_at,
                },
            )
        ]

    def _chunk_transcript(
        self, text: str, source_id: str, title: str, raw_content: dict
    ) -> list[ContentChunk]:
        """
        Chunk transcript into individual feedback-worthy statements.

        Extracts statements from customer speakers that contain feedback keywords.
        """
        # Parse VTT format: timestamp --> timestamp\nSpeaker: text
        pattern = r"\d{2}:\d{2}:\d{2}\.\d{3}\s+-->\s+\d{2}:\d{2}:\d{2}\.\d{3}\r?\n([A-Z][a-z]+\s+[A-Z][a-z]+):\s*(.+?)(?=\r?\n\r?\n|\r?\n\d{2}:|\Z)"
        matches = re.findall(pattern, text, re.DOTALL)

        # Prepare JSON-serializable created_at
        created_at = raw_content.get("created_at")
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        elif created_at is None:
            created_at = datetime.utcnow().isoformat()

        chunks = []
        for idx, (speaker, statement) in enumerate(matches):
            statement = statement.strip()

            # Skip our own employees
            if any(
                name in speaker
                for name in ["Marcus", "Sarah", "PulseDrive", "Product"]
            ):
                continue

            # Check for feedback keywords
            statement_lower = statement.lower()
            if not any(keyword in statement_lower for keyword in FEEDBACK_KEYWORDS):
                continue

            # Create chunk
            chunks.append(
                ContentChunk(
                    id=f"{source_id}_feedback_{idx + 1}",
                    text=f"{speaker}: {statement}",
                    metadata={
                        "title": title,
                        "url": raw_content.get("url"),
                        "parent_transcript_id": source_id,
                        "statement_index": idx + 1,
                        "speaker": speaker,
                        "created_at": created_at,
                    },
                )
            )

        return chunks

    def validate_content(self, raw_content: dict) -> None:
        """Validate Google Drive content structure."""
        super().validate_content(raw_content)

        if "text" not in raw_content:
            raise ValueError("Google Drive content must have 'text' field")

        if not raw_content["text"] or not raw_content["text"].strip():
            raise ValueError("Google Drive content text cannot be empty")
