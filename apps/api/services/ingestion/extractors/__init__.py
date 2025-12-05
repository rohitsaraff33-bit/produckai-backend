"""Source-specific content extractors."""

from apps.api.services.ingestion.extractors.gdrive import GDriveExtractor
from apps.api.services.ingestion.extractors.zoom import ZoomExtractor
from apps.api.services.ingestion.extractors.slack import SlackExtractor
from apps.api.services.ingestion.extractors.jira import JiraExtractor

__all__ = [
    "GDriveExtractor",
    "ZoomExtractor",
    "SlackExtractor",
    "JiraExtractor",
]
