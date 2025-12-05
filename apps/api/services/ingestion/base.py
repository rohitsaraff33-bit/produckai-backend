"""Base classes for content extraction and ingestion."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ContentChunk:
    """A chunk of content extracted from a source."""

    id: str
    text: str
    metadata: dict[str, Any]

    def __post_init__(self):
        """Validate chunk data."""
        if not self.text or not self.text.strip():
            raise ValueError("ContentChunk text cannot be empty")
        if not self.id:
            raise ValueError("ContentChunk id cannot be empty")


@dataclass
class CustomerInfo:
    """Customer information extracted from content."""

    name: str
    confidence: float  # 0.0 to 1.0
    extraction_method: str  # "structured", "regex", "llm", "fallback"
    metadata: dict[str, Any] | None = None


class ContentExtractor(ABC):
    """Abstract base class for source-specific content extraction."""

    @abstractmethod
    def extract_customer(self, raw_content: dict) -> CustomerInfo:
        """
        Extract customer/account information from raw content.

        Args:
            raw_content: Source-specific raw data

        Returns:
            CustomerInfo with name and confidence

        Raises:
            ValueError: If content format is invalid
        """
        pass

    @abstractmethod
    def chunk_content(self, raw_content: dict) -> list[ContentChunk]:
        """
        Chunk content into individual feedback items.

        For long documents/transcripts, break into focused feedback items.
        For short items (tweets, Slack messages), may return single chunk.

        Args:
            raw_content: Source-specific raw data

        Returns:
            List of ContentChunk objects

        Raises:
            ValueError: If content format is invalid
        """
        pass

    @abstractmethod
    def should_chunk(self, raw_content: dict) -> bool:
        """
        Determine if content should be chunked.

        Args:
            raw_content: Source-specific raw data

        Returns:
            True if content should be split into multiple feedback items
        """
        pass

    def validate_content(self, raw_content: dict) -> None:
        """
        Validate raw content structure.

        Args:
            raw_content: Source-specific raw data

        Raises:
            ValueError: If content is invalid
        """
        if not isinstance(raw_content, dict):
            raise ValueError("raw_content must be a dictionary")


@dataclass
class ExtractionStats:
    """Statistics from an extraction operation."""

    total_items: int = 0
    chunks_created: int = 0
    customers_extracted: int = 0
    embeddings_generated: int = 0
    errors: int = 0
    warnings: list[str] | None = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

    def add_warning(self, message: str):
        """Add a warning message."""
        if self.warnings is None:
            self.warnings = []
        self.warnings.append(message)


# Common feedback keywords for chunking logic
FEEDBACK_KEYWORDS = [
    # Issues/Problems
    "issue",
    "problem",
    "concern",
    "bug",
    "error",
    "crash",
    "fail",
    "broken",
    "slow",
    "performance",
    "timeout",
    "outage",
    # Requests/Needs
    "need",
    "want",
    "wish",
    "would like",
    "could use",
    "missing",
    "lack",
    "require",
    "request",
    # Sentiment
    "frustrat",
    "difficult",
    "hard",
    "confusing",
    "annoying",
    "painful",
    # Improvements
    "better",
    "improve",
    "enhance",
    "upgrade",
    "modernize",
    # Features
    "feature",
    "functionality",
    "capability",
    "support",
    "integrate",
    "export",
    "import",
    "api",
    "webhook",
    # UI/UX
    "dashboard",
    "interface",
    "analytics",
    "mobile",
    "design",
    "ux",
    "ui",
    "layout",
    "navigation",
]
