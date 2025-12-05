"""Unified feedback ingestion service."""

from apps.api.services.ingestion.base import ContentChunk, ContentExtractor
from apps.api.services.ingestion.service import FeedbackIngestionService

__all__ = [
    "ContentChunk",
    "ContentExtractor",
    "FeedbackIngestionService",
]
