"""Feedback API endpoints."""

from typing import Optional
from collections import defaultdict

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.database import get_db
from apps.api.models import Feedback, FeedbackSource

logger = structlog.get_logger()
router = APIRouter()


class FeedbackResponse(BaseModel):
    """Feedback item response."""

    id: str
    source: str
    source_id: str
    text: str
    account: Optional[str]
    created_at: str
    meta: Optional[dict] = None

    class Config:
        from_attributes = True


class DocumentSummary(BaseModel):
    """Grouped document summary for source detail pages."""

    document_id: str
    title: str
    url: Optional[str]
    account: Optional[str]
    created_at: str
    modified_at: Optional[str]
    chunk_count: int
    summary: str  # Combined or preview of chunks
    owner: Optional[str]

    class Config:
        from_attributes = True


@router.get("/feedback", response_model=list[FeedbackResponse])
async def list_feedback(
    source: Optional[str] = Query(None, description="Filter by feedback source"),
    limit: int = Query(100, description="Maximum number of items to return"),
    offset: int = Query(0, description="Number of items to skip"),
    db: Session = Depends(get_db),
):
    """
    List feedback items with optional source filtering.

    Args:
        source: Optional source to filter by (slack, jira, zoom_transcript, gdoc, etc.)
        limit: Maximum number of items to return
        offset: Number of items to skip for pagination
        db: Database session

    Returns:
        List of feedback items
    """
    query = db.query(Feedback)

    # Filter by source if provided
    if source:
        try:
            source_enum = FeedbackSource(source)
            query = query.filter(Feedback.source == source_enum)
        except ValueError:
            logger.warning("Invalid source filter", source=source)
            return []

    # Order by creation date (newest first)
    query = query.order_by(Feedback.created_at.desc())

    # Apply pagination
    query = query.offset(offset).limit(limit)

    # Fetch results
    feedback_items = query.all()

    # Convert to response format
    return [
        FeedbackResponse(
            id=str(item.id),
            source=item.source.value,
            source_id=item.source_id,
            text=item.text,
            account=item.account,
            created_at=item.created_at.isoformat(),
            meta=item.meta,
        )
        for item in feedback_items
    ]


@router.get("/feedback/documents", response_model=list[DocumentSummary])
async def list_documents(
    source: Optional[str] = Query(None, description="Filter by feedback source"),
    db: Session = Depends(get_db),
):
    """
    List documents grouped from feedback chunks.

    For sources like Google Drive where transcripts are chunked, this endpoint
    groups chunks back into their parent documents and provides document-level
    summaries.

    Args:
        source: Optional source to filter by (gdoc, zoom_transcript, etc.)
        db: Database session

    Returns:
        List of document summaries
    """
    query = db.query(Feedback)

    # Filter by source if provided
    if source:
        try:
            source_enum = FeedbackSource(source)
            query = query.filter(Feedback.source == source_enum)
        except ValueError:
            logger.warning("Invalid source filter", source=source)
            return []

    # Order by creation date
    query = query.order_by(Feedback.created_at.desc())

    # Fetch all feedback items
    feedback_items = query.all()

    # Group by document
    # Use URL or title as the grouping key to avoid duplicates
    documents = defaultdict(list)

    for item in feedback_items:
        # Determine document ID - prefer URL for deduplication
        meta = item.meta or {}
        doc_url = meta.get("url") or item.doc_url
        doc_title = meta.get("title", "")

        # Use URL as primary key, fallback to title, then source_id
        if doc_url:
            doc_key = doc_url
        elif doc_title:
            doc_key = doc_title
        else:
            # For chunks, use parent_transcript_id from metadata
            # For non-chunked items, use source_id
            doc_key = item.source_id
            if meta:
                parent_id = meta.get("parent_transcript_id")
                if parent_id:
                    doc_key = parent_id

        documents[doc_key].append(item)

    # Build document summaries
    summaries = []
    for doc_id, chunks in documents.items():
        # Sort chunks by created_at to get consistent ordering
        chunks.sort(key=lambda x: x.created_at)

        # Get document metadata from first chunk (they should all have same doc metadata)
        first_chunk = chunks[0]
        meta = first_chunk.meta or {}

        # Combine chunk texts for summary
        # For display purposes, we'll create a preview from first few chunks
        chunk_texts = [chunk.text for chunk in chunks[:5]]  # First 5 chunks
        summary_text = " ... ".join(chunk_texts)

        # Truncate if too long
        if len(summary_text) > 500:
            summary_text = summary_text[:497] + "..."

        # Add indicator if there are more chunks
        if len(chunks) > 5:
            summary_text += f" [+{len(chunks) - 5} more statements]"

        summaries.append(
            DocumentSummary(
                document_id=doc_id,
                title=meta.get("title", f"Document {doc_id[:8]}"),
                url=meta.get("url") or first_chunk.doc_url,
                account=first_chunk.account,
                created_at=first_chunk.created_at.isoformat(),
                modified_at=meta.get("modified_time"),
                chunk_count=len(chunks),
                summary=summary_text,
                owner=meta.get("owner"),
            )
        )

    # Sort by created_at descending
    summaries.sort(key=lambda x: x.created_at, reverse=True)

    return summaries
