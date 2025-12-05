"""Google Drive and Docs API client."""

from datetime import datetime
from typing import List, Optional

import httpx
import structlog
from sqlalchemy.orm import Session

from apps.api.config import get_settings
from apps.api.core.secrets import get_secrets_manager
from apps.api.models import FeedbackSource, OAuthProvider, OAuthToken, TokenStatus

logger = structlog.get_logger()
settings = get_settings()


class GoogleDriveClient:
    """Client for interacting with Google Drive and Docs APIs."""

    BASE_URL = "https://www.googleapis.com/drive/v3"
    DOCS_URL = "https://www.googleapis.com/docs/v1"

    def __init__(self, access_token: str):
        """
        Initialize Google Drive client with access token.

        Args:
            access_token: OAuth access token
        """
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    @classmethod
    def from_db(cls, db: Session) -> Optional["GoogleDriveClient"]:
        """
        Create Google Drive client from database token.

        Args:
            db: Database session

        Returns:
            GoogleDriveClient instance or None if no valid token found
        """
        # Get active token
        token = (
            db.query(OAuthToken)
            .filter(
                OAuthToken.provider == OAuthProvider.google,
                OAuthToken.status == TokenStatus.active,
                OAuthToken.expires_at > datetime.utcnow(),
            )
            .first()
        )

        if not token:
            logger.warning("No valid Google OAuth token found")
            return None

        # Decrypt access token
        secrets_mgr = get_secrets_manager()
        try:
            # Parse "nonce|ciphertext" format
            nonce, ciphertext = token.access_token_enc.split("|", 1)
            access_token = secrets_mgr.decrypt(nonce, ciphertext)
        except Exception as e:
            logger.error("Failed to decrypt Google access token", error=str(e))
            return None

        return cls(access_token)

    async def list_files_in_folders(self, folder_ids: List[str]) -> List[dict]:
        """
        List all Google Docs files in specified folders.

        Args:
            folder_ids: List of Google Drive folder IDs

        Returns:
            List of file metadata dicts
        """
        all_files = []

        async with httpx.AsyncClient() as client:
            for folder_id in folder_ids:
                try:
                    # Query for Google Docs in this folder
                    query = (
                        f"'{folder_id}' in parents and "
                        f"mimeType='application/vnd.google-apps.document' and "
                        f"trashed=false"
                    )

                    response = await client.get(
                        f"{self.BASE_URL}/files",
                        headers=self.headers,
                        params={
                            "q": query,
                            "fields": "files(id,name,webViewLink,owners,modifiedTime)",
                            "pageSize": 100,
                        },
                    )
                    response.raise_for_status()
                    data = response.json()

                    files = data.get("files", [])
                    all_files.extend(files)

                    logger.info(
                        "Found Google Docs in folder",
                        folder_id=folder_id,
                        count=len(files),
                    )

                except Exception as e:
                    logger.error(
                        "Error listing files in folder", folder_id=folder_id, error=str(e)
                    )

        return all_files

    async def get_document_content(self, document_id: str, title: str = "Untitled") -> dict:
        """
        Get full content of a Google Doc using Drive API export.

        Args:
            document_id: Google Doc ID
            title: Document title (from file metadata)

        Returns:
            Dict with 'text' and 'title' keys
        """
        try:
            async with httpx.AsyncClient() as client:
                # Use Drive API export to get plain text content
                # This works better than Docs API for simple text extraction
                response = await client.get(
                    f"{self.BASE_URL}/files/{document_id}/export",
                    headers=self.headers,
                    params={"mimeType": "text/plain"},
                )
                response.raise_for_status()

                # Get the plain text content
                text = response.text.strip()

                return {"title": title, "text": text}

        except Exception as e:
            logger.error(
                "Error exporting document", document_id=document_id, error=str(e)
            )
            return {"title": title, "text": ""}


async def sync_google_docs(db: Session, folder_ids: List[str]) -> dict:
    """
    Sync Google Docs from specified folders to feedback database.

    Uses unified FeedbackIngestionService for consistent processing.

    Args:
        db: Database session
        folder_ids: List of Google Drive folder IDs to sync

    Returns:
        Sync statistics dict
    """
    from apps.api.services.ingestion import FeedbackIngestionService
    from apps.api.services.ingestion.extractors import GDriveExtractor

    client = GoogleDriveClient.from_db(db)
    if not client:
        return {"error": "No valid Google OAuth token found"}

    if not folder_ids:
        return {"error": "No folder IDs provided"}

    # Initialize ingestion service and extractor
    ingestion_service = FeedbackIngestionService(db)
    extractor = GDriveExtractor()

    stats = {
        "files_found": 0,
        "documents_processed": 0,
        "chunks_created": 0,
        "feedback_created": 0,
        "feedback_updated": 0,
        "embeddings_generated": 0,
        "errors": 0,
        "warnings": [],
    }

    try:
        # Fetch files from folders
        files = await client.list_files_in_folders(folder_ids)
        stats["files_found"] = len(files)

        logger.info("Found Google Docs", count=len(files))

        # Prepare raw content for batch ingestion
        raw_items = []
        for file in files:
            doc_id = file.get("id")
            doc_name = file.get("name", "Untitled")
            doc_url = file.get("webViewLink", "")
            modified_time = file.get("modifiedTime")

            # Get document content
            doc_content = await client.get_document_content(doc_id, title=doc_name)
            if not doc_content or not doc_content.get("text"):
                stats["errors"] += 1
                continue

            stats["documents_processed"] += 1

            # Get owner info
            owners = file.get("owners", [])
            owner_email = owners[0].get("emailAddress", "") if owners else ""

            # Prepare raw content for extractor
            raw_content = {
                "text": doc_content.get("text"),
                "source_id": doc_id,
                "title": doc_name,
                "url": doc_url,
                "modified_time": modified_time,
                "owner": owner_email,
                "created_at": datetime.fromisoformat(modified_time.replace("Z", "+00:00"))
                if modified_time
                else datetime.utcnow(),
            }
            raw_items.append(raw_content)

        # Batch ingest using unified service
        # This handles customer extraction, chunking, embedding generation, etc.
        feedback_items, ingestion_stats = ingestion_service.ingest_batch(
            source=FeedbackSource.gdoc,
            raw_items=raw_items,
            extractor=extractor,
            batch_size=10,
        )

        # Aggregate statistics
        stats["chunks_created"] = ingestion_stats.chunks_created
        stats["embeddings_generated"] = ingestion_stats.embeddings_generated
        stats["errors"] += ingestion_stats.errors
        stats["warnings"] = ingestion_stats.warnings or []

        # Count feedback created/updated
        # (ingestion service doesn't track this separately, so approximate)
        stats["feedback_created"] = len(feedback_items)

        logger.info(
            "Google Drive sync completed",
            files_found=stats["files_found"],
            documents_processed=stats["documents_processed"],
            chunks_created=stats["chunks_created"],
            embeddings_generated=stats["embeddings_generated"],
            errors=stats["errors"],
        )

    except Exception as e:
        logger.error("Google Drive sync failed", error=str(e))
        stats["errors"] += 1
        db.rollback()

    return stats
