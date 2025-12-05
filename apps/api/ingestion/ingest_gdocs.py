"""Google Docs ingestion - demo and live modes."""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from apps.api.config import get_settings
from apps.api.database import get_db_context
from apps.api.models import Feedback, FeedbackSource
from apps.api.services.chunking import get_chunking_service
from apps.api.services.embeddings import get_embedding_service
from apps.api.services.google_client import get_google_docs_client
from apps.api.services.pii_redaction import get_pii_redaction_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


def normalize_gdoc_text(text: str) -> str:
    """Normalize Google Docs text by removing boilerplate and preserving structure.

    Args:
        text: Raw text from Google Doc

    Returns:
        Normalized text
    """
    # Remove excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Remove common boilerplate patterns
    text = re.sub(r'Table of Contents.*?\n\n', '', text, flags=re.IGNORECASE | re.DOTALL)

    # Preserve bullet structure by normalizing to dashes
    text = re.sub(r'^[\u2022\u2023\u25E6\u2043\u2219]\s+', '- ', text, flags=re.MULTILINE)

    return text.strip()


def ingest_gdocs_demo(db: Session) -> int:
    """Ingest demo Google Docs files from /samples/gdocs.

    Args:
        db: Database session

    Returns:
        Number of feedback items created
    """
    samples_dir = Path('/app/samples') if Path('/app/samples').exists() else Path('samples')
    gdocs_dir = samples_dir / 'gdocs'

    if not gdocs_dir.exists():
        logger.warning(f"Google Docs samples directory not found: {gdocs_dir}")
        return 0

    chunking_service = get_chunking_service(chunk_size=500, overlap=50, split_on_headers=True)
    pii_service = get_pii_redaction_service()
    embedding_service = get_embedding_service()

    feedback_items = []

    # Process all .md and .txt files
    for file_path in gdocs_dir.glob('*.md'):
        logger.info(f"Processing demo file: {file_path.name}")

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Normalize text
        normalized = normalize_gdoc_text(content)

        # Extract title (first H1 or filename)
        title_match = re.match(r'^#\s+(.+)$', normalized, re.MULTILINE)
        title = title_match.group(1) if title_match else file_path.stem

        # Chunk the document
        chunks = chunking_service.chunk_text(
            normalized, metadata={'filename': file_path.name, 'title': title}
        )

        logger.info(f"Created {len(chunks)} chunks from {file_path.name}")

        # Create feedback items for each chunk
        for chunk in chunks:
            # Redact PII
            redacted_text = pii_service.redact(chunk.text)

            feedback = Feedback(
                id=uuid4(),
                source=FeedbackSource.gdoc,
                source_id=f"{file_path.stem}_chunk_{chunk.chunk_idx}",
                account='Demo',
                text=redacted_text,
                created_at=datetime.utcnow(),
                doc_url=f"file://{file_path}",  # Demo mode uses file:// URLs
                meta={
                    'filename': file_path.name,
                    'title': title,
                    'chunk_idx': chunk.chunk_idx,
                    'total_chunks': len(chunks),
                    'header_level': chunk.metadata.get('header_level', 0),
                },
            )
            feedback_items.append(feedback)

    # Batch add to database
    if feedback_items:
        for item in feedback_items:
            db.add(item)
        db.commit()

        # Generate embeddings
        logger.info(f"Generating embeddings for {len(feedback_items)} chunks...")
        texts = [f.text for f in feedback_items]
        embeddings = embedding_service.embed_batch(texts)

        for feedback, embedding in zip(feedback_items, embeddings):
            feedback.embedding = embedding

        db.commit()
        logger.info(f"Ingested {len(feedback_items)} feedback items from Google Docs demo")

    return len(feedback_items)


def ingest_gdocs_live(db: Session, folder_ids: Optional[List[str]] = None) -> int:
    """Ingest Google Docs from live Drive API.

    Args:
        db: Database session
        folder_ids: List of folder IDs to ingest from (defaults to env config)

    Returns:
        Number of feedback items created
    """
    folder_ids = folder_ids or getattr(settings, 'drive_folder_ids', '').split(',')
    folder_ids = [fid.strip() for fid in folder_ids if fid.strip()]

    if not folder_ids:
        raise ValueError("No folder IDs specified. Set DRIVE_FOLDER_IDS in .env or pass folder_ids")

    logger.info(f"Ingesting Google Docs from {len(folder_ids)} folders...")

    google_client = get_google_docs_client()
    chunking_service = get_chunking_service(chunk_size=500, overlap=50, split_on_headers=True)
    pii_service = get_pii_redaction_service()
    embedding_service = get_embedding_service()

    feedback_items = []

    # List all docs in folders
    files = google_client.list_files_in_folders(folder_ids)
    logger.info(f"Found {len(files)} Google Docs to process")

    for file_meta in files:
        try:
            doc_id = file_meta['id']
            logger.info(f"Processing doc: {file_meta.get('name', doc_id)}")

            # Get document content
            doc_content = google_client.get_document_content(doc_id)
            title = doc_content['title']
            text = doc_content['text']

            if not text:
                logger.warning(f"Empty document: {title}")
                continue

            # Normalize text
            normalized = normalize_gdoc_text(text)

            # Extract owner domain for account mapping
            account = google_client.extract_owner_domain(file_meta) or 'Unknown'

            # Get modified time
            modified_time = datetime.fromisoformat(
                file_meta['modifiedTime'].replace('Z', '+00:00')
            )

            # Chunk the document
            chunks = chunking_service.chunk_text(
                normalized,
                metadata={
                    'doc_id': doc_id,
                    'title': title,
                    'headings': doc_content.get('headings', []),
                },
            )

            logger.info(f"Created {len(chunks)} chunks from {title}")

            # Create feedback items
            for chunk in chunks:
                # Redact PII
                redacted_text = pii_service.redact(chunk.text)

                feedback = Feedback(
                    id=uuid4(),
                    source=FeedbackSource.gdoc,
                    source_id=f"{doc_id}_chunk_{chunk.chunk_idx}",
                    account=account,
                    text=redacted_text,
                    created_at=modified_time,
                    doc_url=file_meta.get('webViewLink'),
                    meta={
                        'gdoc_id': doc_id,
                        'title': title,
                        'chunk_idx': chunk.chunk_idx,
                        'total_chunks': len(chunks),
                        'owner': file_meta.get('owners', [{}])[0].get('emailAddress'),
                        'last_modified_by': file_meta.get('lastModifyingUser', {}).get(
                            'emailAddress'
                        ),
                        'modified_time': modified_time.isoformat(),
                        'header_level': chunk.metadata.get('header_level', 0),
                        'headings': doc_content.get('headings', []),
                    },
                )
                feedback_items.append(feedback)

        except Exception as e:
            logger.error(f"Error processing doc {file_meta.get('id')}: {e}")

    # Batch add to database
    if feedback_items:
        for item in feedback_items:
            db.add(item)
        db.commit()

        # Generate embeddings
        logger.info(f"Generating embeddings for {len(feedback_items)} chunks...")
        texts = [f.text for f in feedback_items]
        embeddings = embedding_service.embed_batch(texts)

        for feedback, embedding in zip(feedback_items, embeddings):
            feedback.embedding = embedding

        db.commit()
        logger.info(f"Ingested {len(feedback_items)} feedback items from Google Docs live")

    return len(feedback_items)


if __name__ == '__main__':
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else 'demo'

    with get_db_context() as db:
        if mode == 'demo':
            count = ingest_gdocs_demo(db)
        elif mode == 'live':
            count = ingest_gdocs_live(db)
        else:
            raise ValueError(f"Unknown mode: {mode}. Use 'demo' or 'live'")

        logger.info(f"✓ Ingested {count} feedback items from Google Docs ({mode} mode)")
