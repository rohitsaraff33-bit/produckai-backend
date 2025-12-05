"""Competitive Intelligence API endpoints."""

from typing import List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.database import get_db
from apps.api.models import CompetitiveInsightMetadata, Insight, InsightCategory, ResearchSession
from apps.api.services.competitive_intel import CompetitiveIntelligenceAgent

logger = structlog.get_logger()
router = APIRouter()


class CompetitorMoveInput(BaseModel):
    """Single competitor move input."""

    move: str  # Description of the move
    date: str  # Date of the move
    source_url: str  # URL source for this move


class CompetitorDataInput(BaseModel):
    """Competitor data provided by PM (Manual Mode)."""

    name: str  # Competitor name
    description: str  # Context about this competitor
    moves: List[CompetitorMoveInput]  # List of recent moves


class ManualResearchRequest(BaseModel):
    """Request to process manual competitive intelligence input."""

    company_name: str  # Your company name
    market_scope: str  # e.g., "B2B sales intelligence"
    target_personas: List[str]  # ["SDR", "AE", "RevOps"]
    geo_segments: List[str]  # ["NA", "EU", "SMB", "ENT"]
    competitor_data: List[CompetitorDataInput]  # PM-provided competitor data
    time_window_months: str = "12"  # How far back to analyze


class AutoResearchRequest(BaseModel):
    """Request for auto competitive intelligence research (minimal input)."""

    company_name: str  # Your company name
    market_scope: str  # e.g., "Product Management Software"
    competitor_names: Optional[List[str]] = None  # Optional list of competitors (AI will find if not provided)
    target_personas: Optional[List[str]] = None  # Optional personas (AI will infer if not provided)
    geo_segments: Optional[List[str]] = None  # Optional segments (AI will infer if not provided)
    time_window_months: str = "12"  # How far back to analyze


class ResearchSessionResponse(BaseModel):
    """Research session response."""

    id: str
    company_name: str
    market_scope: str
    target_personas: List[str]
    geo_segments: List[str]
    competitors_researched: List[str]
    insights_generated: Optional[List[str]]
    status: str  # running, completed, failed
    error_message: Optional[str]
    started_at: str
    completed_at: Optional[str]

    class Config:
        from_attributes = True


class CompetitiveInsightResponse(BaseModel):
    """Competitive insight with metadata."""

    # Core insight
    id: str
    title: str
    description: Optional[str]
    impact: Optional[str]
    recommendation: Optional[str]
    severity: str
    effort: str
    priority_score: int
    created_at: str

    # Competitive metadata
    competitor_name: str
    competitor_moves: Optional[List[dict]]
    evidence_count: Optional[str]
    mentions_30d: Optional[str]
    impacted_acv_usd: Optional[str]
    est_method: Optional[str]
    citations: Optional[List[dict]]

    class Config:
        from_attributes = True


@router.post("/process-manual", response_model=ResearchSessionResponse)
async def process_manual_competitive_input(
    request: ManualResearchRequest,
    db: Session = Depends(get_db),
):
    """
    Process manual competitive intelligence input (Manual Mode - Option C).

    PM provides competitor data → Agent formats as PM-ready insight cards.

    Args:
        request: Manual research request with competitor data
        db: Database session

    Returns:
        Research session with generated insight IDs
    """
    try:
        logger.info(
            "Received manual competitive intelligence request",
            company=request.company_name,
            competitors_count=len(request.competitor_data),
        )

        # Initialize agent
        agent = CompetitiveIntelligenceAgent()

        # Convert Pydantic models to dicts for agent
        competitor_data = [
            {
                "name": comp.name,
                "description": comp.description,
                "moves": [
                    {
                        "move": move.move,
                        "date": move.date,
                        "source_url": move.source_url,
                    }
                    for move in comp.moves
                ],
            }
            for comp in request.competitor_data
        ]

        # Process manual input
        session = await agent.process_manual_input(
            db=db,
            company_name=request.company_name,
            market_scope=request.market_scope,
            target_personas=request.target_personas,
            geo_segments=request.geo_segments,
            competitor_data=competitor_data,
            time_window_months=request.time_window_months,
        )

        return ResearchSessionResponse(
            id=str(session.id),
            company_name=session.company_name,
            market_scope=session.market_scope,
            target_personas=session.target_personas,
            geo_segments=session.geo_segments,
            competitors_researched=session.competitors_researched,
            insights_generated=session.insights_generated,
            status=session.status,
            error_message=session.error_message,
            started_at=session.started_at.isoformat(),
            completed_at=session.completed_at.isoformat() if session.completed_at else None,
        )

    except Exception as e:
        logger.error("Failed to process manual competitive input", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-auto", response_model=ResearchSessionResponse)
async def process_auto_competitive_research(
    request: AutoResearchRequest,
    db: Session = Depends(get_db),
):
    """
    Process auto competitive intelligence research (Auto Mode).

    PM provides minimal input → AI researches competitors and generates insight cards.

    Requires only company_name and market_scope. AI will:
    - Identify relevant competitors (if not provided)
    - Research recent product moves using web search
    - Generate PM-ready insight cards with citations

    Args:
        request: Auto research request with minimal input
        db: Database session

    Returns:
        Research session with generated insight IDs
    """
    try:
        logger.info(
            "Received auto competitive intelligence request",
            company=request.company_name,
            market=request.market_scope,
            competitors_provided=len(request.competitor_names) if request.competitor_names else 0,
        )

        # Initialize agent
        agent = CompetitiveIntelligenceAgent()

        # If no competitors provided, let AI identify them
        # Otherwise use provided list
        competitor_names = request.competitor_names or []

        # Default personas and segments if not provided
        target_personas = request.target_personas or ["Product Managers", "Product Leaders", "Engineering"]
        geo_segments = request.geo_segments or ["Global", "Enterprise", "SMB"]

        # Run auto research
        session = await agent.run_research(
            db=db,
            company_name=request.company_name,
            market_scope=request.market_scope,
            target_personas=target_personas,
            geo_segments=geo_segments,
            competitor_names=competitor_names,
            time_window_months=request.time_window_months,
        )

        return ResearchSessionResponse(
            id=str(session.id),
            company_name=session.company_name,
            market_scope=session.market_scope,
            target_personas=session.target_personas,
            geo_segments=session.geo_segments,
            competitors_researched=session.competitors_researched,
            insights_generated=session.insights_generated,
            status=session.status,
            error_message=session.error_message,
            started_at=session.started_at.isoformat(),
            completed_at=session.completed_at.isoformat() if session.completed_at else None,
        )

    except Exception as e:
        logger.error("Failed to process auto competitive research", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=List[ResearchSessionResponse])
async def list_research_sessions(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    List competitive intelligence research sessions.

    Args:
        limit: Maximum number of sessions to return
        offset: Pagination offset
        db: Database session

    Returns:
        List of research sessions
    """
    sessions = (
        db.query(ResearchSession)
        .order_by(ResearchSession.started_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        ResearchSessionResponse(
            id=str(s.id),
            company_name=s.company_name,
            market_scope=s.market_scope,
            target_personas=s.target_personas,
            geo_segments=s.geo_segments,
            competitors_researched=s.competitors_researched,
            insights_generated=s.insights_generated,
            status=s.status,
            error_message=s.error_message,
            started_at=s.started_at.isoformat(),
            completed_at=s.completed_at.isoformat() if s.completed_at else None,
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}", response_model=ResearchSessionResponse)
async def get_research_session(
    session_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get specific research session details.

    Args:
        session_id: Research session UUID
        db: Database session

    Returns:
        Research session details
    """
    session = db.query(ResearchSession).filter(ResearchSession.id == session_id).first()

    if not session:
        raise HTTPException(status_code=404, detail="Research session not found")

    return ResearchSessionResponse(
        id=str(session.id),
        company_name=session.company_name,
        market_scope=session.market_scope,
        target_personas=session.target_personas,
        geo_segments=session.geo_segments,
        competitors_researched=session.competitors_researched,
        insights_generated=session.insights_generated,
        status=session.status,
        error_message=session.error_message,
        started_at=session.started_at.isoformat(),
        completed_at=session.completed_at.isoformat() if session.completed_at else None,
    )


@router.get("/insights", response_model=List[CompetitiveInsightResponse])
async def list_competitive_insights(
    limit: int = 20,
    offset: int = 0,
    competitor_name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    List competitive intelligence insights.

    Args:
        limit: Maximum number of insights to return
        offset: Pagination offset
        competitor_name: Optional filter by competitor name
        db: Database session

    Returns:
        List of competitive insights with metadata
    """
    # Query insights with competitive category
    query = db.query(Insight).filter(Insight.category == InsightCategory.competitive_intel)

    # Join with metadata for filtering
    if competitor_name:
        query = query.join(
            CompetitiveInsightMetadata,
            Insight.id == CompetitiveInsightMetadata.insight_id
        ).filter(CompetitiveInsightMetadata.competitor_name == competitor_name)

    query = query.order_by(Insight.priority_score.desc())
    insights = query.offset(offset).limit(limit).all()

    # Build response with metadata
    results = []
    for insight in insights:
        # Get metadata
        metadata = (
            db.query(CompetitiveInsightMetadata)
            .filter(CompetitiveInsightMetadata.insight_id == insight.id)
            .first()
        )

        results.append(
            CompetitiveInsightResponse(
                id=str(insight.id),
                title=insight.title,
                description=insight.description,
                impact=insight.impact,
                recommendation=insight.recommendation,
                severity=insight.severity or "medium",
                effort=insight.effort or "medium",
                priority_score=insight.priority_score,
                created_at=insight.created_at.isoformat(),
                competitor_name=metadata.competitor_name if metadata else "Unknown",
                competitor_moves=metadata.competitor_moves if metadata else None,
                evidence_count=metadata.evidence_count if metadata else None,
                mentions_30d=metadata.mentions_30d if metadata else None,
                impacted_acv_usd=metadata.impacted_acv_usd if metadata else None,
                est_method=metadata.est_method if metadata else None,
                citations=metadata.citations if metadata else None,
            )
        )

    return results


@router.get("/insights/{insight_id}", response_model=CompetitiveInsightResponse)
async def get_competitive_insight(
    insight_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get detailed competitive insight.

    Args:
        insight_id: Insight UUID
        db: Database session

    Returns:
        Competitive insight with full metadata
    """
    insight = (
        db.query(Insight)
        .filter(Insight.id == insight_id, Insight.category == InsightCategory.competitive_intel)
        .first()
    )

    if not insight:
        raise HTTPException(status_code=404, detail="Competitive insight not found")

    # Get metadata
    metadata = (
        db.query(CompetitiveInsightMetadata)
        .filter(CompetitiveInsightMetadata.insight_id == insight.id)
        .first()
    )

    return CompetitiveInsightResponse(
        id=str(insight.id),
        title=insight.title,
        description=insight.description,
        impact=insight.impact,
        recommendation=insight.recommendation,
        severity=insight.severity or "medium",
        effort=insight.effort or "medium",
        priority_score=insight.priority_score,
        created_at=insight.created_at.isoformat(),
        competitor_name=metadata.competitor_name if metadata else "Unknown",
        competitor_moves=metadata.competitor_moves if metadata else None,
        evidence_count=metadata.evidence_count if metadata else None,
        mentions_30d=metadata.mentions_30d if metadata else None,
        impacted_acv_usd=metadata.impacted_acv_usd if metadata else None,
        est_method=metadata.est_method if metadata else None,
        citations=metadata.citations if metadata else None,
    )
