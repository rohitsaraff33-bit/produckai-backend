"""Ingestion endpoints."""

from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from apps.api.database import get_db
from apps.api.models import Feedback, FeedbackSource

router = APIRouter()


class IngestResponse(BaseModel):
    """Ingest task response."""

    status: str
    message: str
    count: int


@router.post("/slack", response_model=IngestResponse)
async def ingest_slack(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Ingest Slack data (demo or live based on DEMO_MODE).

    Returns:
        Status of ingestion
    """
    from apps.api.scripts.ingest_slack import ingest_slack_data

    count = ingest_slack_data()

    return IngestResponse(
        status="completed",
        message=f"Ingested {count} Slack messages",
        count=count,
    )


@router.post("/jira", response_model=IngestResponse)
async def ingest_jira(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Ingest Jira data (demo or live based on DEMO_MODE).

    Returns:
        Status of ingestion
    """
    from apps.api.scripts.ingest_jira import ingest_jira_data

    count = ingest_jira_data()

    return IngestResponse(
        status="completed",
        message=f"Ingested {count} Jira issues",
        count=count,
    )


class GDocsIngestRequest(BaseModel):
    """Google Docs ingest request."""

    mode: str = "demo"  # "demo" or "live"
    folder_ids: Optional[List[str]] = None


@router.post("/gdocs", response_model=IngestResponse)
async def ingest_gdocs(
    request: GDocsIngestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Ingest Google Docs data.

    Args:
        request: Mode and optional folder IDs
        db: Database session

    Returns:
        Status of ingestion
    """
    from apps.api.ingestion.ingest_gdocs import ingest_gdocs_demo, ingest_gdocs_live

    if request.mode == "demo":
        count = ingest_gdocs_demo(db)
    elif request.mode == "live":
        count = ingest_gdocs_live(db, folder_ids=request.folder_ids)
    else:
        return IngestResponse(
            status="error",
            message=f"Invalid mode: {request.mode}. Use 'demo' or 'live'",
            count=0,
        )

    return IngestResponse(
        status="completed",
        message=f"Ingested {count} Google Docs chunks",
        count=count,
    )


class ZoomIngestRequest(BaseModel):
    """Zoom ingest request."""

    mode: str = "demo"  # "demo" or "live"
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None  # YYYY-MM-DD
    user_id: Optional[str] = None


@router.post("/zoom", response_model=IngestResponse)
async def ingest_zoom(
    request: ZoomIngestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Ingest Zoom transcript data.

    Args:
        request: Mode and optional date range
        db: Database session

    Returns:
        Status of ingestion
    """
    from apps.api.ingestion.ingest_zoom import ingest_zoom_demo, ingest_zoom_live

    if request.mode == "demo":
        count = ingest_zoom_demo(db)
    elif request.mode == "live":
        count = ingest_zoom_live(
            db,
            start_date=request.start_date,
            end_date=request.end_date,
            user_id=request.user_id,
        )
    else:
        return IngestResponse(
            status="error",
            message=f"Invalid mode: {request.mode}. Use 'demo' or 'live'",
            count=0,
        )

    return IngestResponse(
        status="completed",
        message=f"Ingested {count} Zoom transcript chunks",
        count=count,
    )


class SourceSummary(BaseModel):
    """Summary of feedback by source."""

    source: str
    count: int
    last_ingested_at: Optional[str] = None


class SourcesSummaryResponse(BaseModel):
    """Sources summary response."""

    sources: List[SourceSummary]
    total_count: int


@router.get("/sources/summary", response_model=SourcesSummaryResponse)
async def get_sources_summary(db: Session = Depends(get_db)):
    """
    Get summary of feedback items by source.

    Returns:
        Count and last ingested timestamp for each source
    """
    # Query counts by source
    source_counts = (
        db.query(
            Feedback.source,
            func.count(Feedback.id).label('count'),
            func.max(Feedback.created_at).label('last_ingested_at'),
        )
        .group_by(Feedback.source)
        .all()
    )

    sources = []
    total_count = 0

    for source, count, last_ingested in source_counts:
        sources.append(
            SourceSummary(
                source=source.value if hasattr(source, 'value') else str(source),
                count=count,
                last_ingested_at=last_ingested.isoformat() if last_ingested else None,
            )
        )
        total_count += count

    return SourcesSummaryResponse(sources=sources, total_count=total_count)
