"""Jira VOC scoring API endpoints."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.database import get_db
from apps.api.models import (
    Insight,
    JiraInsightMatch,
    JiraTicket,
    JiraTicketPriority,
    JiraTicketStatus,
    VOCScore,
)
from apps.api.services.embeddings import get_embedding_service
from apps.api.services.voc_scoring import get_voc_scoring_service

logger = structlog.get_logger()
router = APIRouter()


class JiraTicketCreate(BaseModel):
    """Request model for creating a Jira ticket."""

    jira_key: str
    title: str
    description: Optional[str] = None
    status: JiraTicketStatus = JiraTicketStatus.BACKLOG
    priority: JiraTicketPriority = JiraTicketPriority.MEDIUM
    assignee: Optional[str] = None
    reporter: Optional[str] = None
    labels: Optional[List[str]] = None
    epic_key: Optional[str] = None
    story_points: Optional[int] = None


class JiraTicketResponse(BaseModel):
    """Response model for Jira ticket."""

    id: str
    jira_key: str
    title: str
    description: Optional[str]
    status: str
    priority: str
    assignee: Optional[str]
    reporter: Optional[str]
    labels: Optional[List[str]]
    epic_key: Optional[str]
    story_points: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InsightMatchResponse(BaseModel):
    """Response model for Jira-Insight match."""

    insight_id: str
    insight_title: str
    similarity_score: float
    confidence: str
    is_confirmed: Optional[int]

    class Config:
        from_attributes = True


class VOCScoreResponse(BaseModel):
    """Response model for VOC score."""

    ticket_id: str
    customer_count: int
    total_acv: float
    feedback_volume: int
    ent_customer_count: int
    mm_customer_count: int
    smb_customer_count: int
    customer_score: float
    acv_score: float
    segment_score: float
    volume_score: float
    voc_score: float
    recommended_priority: str
    calculated_at: datetime

    class Config:
        from_attributes = True


class JiraTicketWithVOC(BaseModel):
    """Response model for Jira ticket with VOC score."""

    ticket: JiraTicketResponse
    voc_score: Optional[VOCScoreResponse]
    matched_insights: List[InsightMatchResponse]


@router.post("/jira/tickets", response_model=JiraTicketResponse)
async def create_ticket(ticket_data: JiraTicketCreate, db: Session = Depends(get_db)):
    """
    Create a new Jira ticket.

    Args:
        ticket_data: Ticket data
        db: Database session

    Returns:
        Created ticket
    """
    # Check if ticket already exists
    existing = (
        db.query(JiraTicket)
        .filter(JiraTicket.jira_key == ticket_data.jira_key)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Ticket with key {ticket_data.jira_key} already exists",
        )

    # Generate embedding for ticket
    embedding_service = get_embedding_service()
    ticket_text = f"{ticket_data.title}. {ticket_data.description or ''}"
    embedding = embedding_service.embed_text(ticket_text)

    # Create ticket
    ticket = JiraTicket(
        jira_key=ticket_data.jira_key,
        title=ticket_data.title,
        description=ticket_data.description,
        status=ticket_data.status,
        priority=ticket_data.priority,
        assignee=ticket_data.assignee,
        reporter=ticket_data.reporter,
        labels=ticket_data.labels,
        epic_key=ticket_data.epic_key,
        story_points=ticket_data.story_points,
        embedding=embedding,
    )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    logger.info(f"Created Jira ticket: {ticket.jira_key}")

    return JiraTicketResponse(
        id=str(ticket.id),
        jira_key=ticket.jira_key,
        title=ticket.title,
        description=ticket.description,
        status=ticket.status.value,
        priority=ticket.priority.value,
        assignee=ticket.assignee,
        reporter=ticket.reporter,
        labels=ticket.labels,
        epic_key=ticket.epic_key,
        story_points=ticket.story_points,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


@router.get("/jira/tickets", response_model=List[JiraTicketWithVOC])
async def list_tickets(
    status: Optional[str] = Query(None, description="Filter by status"),
    min_voc_score: Optional[float] = Query(None, description="Minimum VOC score"),
    sort_by: str = Query("voc_score", description="Sort by: voc_score, created_at, priority"),
    db: Session = Depends(get_db),
):
    """
    List Jira tickets with VOC scores.

    Args:
        status: Filter by ticket status
        min_voc_score: Minimum VOC score
        sort_by: Sort field
        db: Database session

    Returns:
        List of tickets with VOC scores
    """
    query = db.query(JiraTicket)

    # Apply filters
    if status:
        try:
            status_enum = JiraTicketStatus(status)
            query = query.filter(JiraTicket.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    tickets = query.all()

    # Build response with VOC scores
    results = []
    for ticket in tickets:
        # Get VOC score
        voc_score = (
            db.query(VOCScore)
            .filter(VOCScore.ticket_id == ticket.id)
            .first()
        )

        # Apply VOC score filter
        if min_voc_score and (not voc_score or voc_score.voc_score < min_voc_score):
            continue

        # Get matched insights
        matches = (
            db.query(JiraInsightMatch)
            .filter(JiraInsightMatch.ticket_id == ticket.id)
            .all()
        )

        matched_insights = []
        for match in matches:
            insight = db.query(Insight).filter(Insight.id == match.insight_id).first()
            if insight:
                matched_insights.append(
                    InsightMatchResponse(
                        insight_id=str(insight.id),
                        insight_title=insight.title,
                        similarity_score=match.similarity_score,
                        confidence=match.confidence,
                        is_confirmed=match.is_confirmed,
                    )
                )

        results.append(
            JiraTicketWithVOC(
                ticket=JiraTicketResponse(
                    id=str(ticket.id),
                    jira_key=ticket.jira_key,
                    title=ticket.title,
                    description=ticket.description,
                    status=ticket.status.value,
                    priority=ticket.priority.value,
                    assignee=ticket.assignee,
                    reporter=ticket.reporter,
                    labels=ticket.labels,
                    epic_key=ticket.epic_key,
                    story_points=ticket.story_points,
                    created_at=ticket.created_at,
                    updated_at=ticket.updated_at,
                ),
                voc_score=VOCScoreResponse(
                    ticket_id=str(voc_score.ticket_id),
                    customer_count=voc_score.customer_count,
                    total_acv=voc_score.total_acv,
                    feedback_volume=voc_score.feedback_volume,
                    ent_customer_count=voc_score.ent_customer_count,
                    mm_customer_count=voc_score.mm_customer_count,
                    smb_customer_count=voc_score.smb_customer_count,
                    customer_score=voc_score.customer_score,
                    acv_score=voc_score.acv_score,
                    segment_score=voc_score.segment_score,
                    volume_score=voc_score.volume_score,
                    voc_score=voc_score.voc_score,
                    recommended_priority=voc_score.recommended_priority,
                    calculated_at=voc_score.calculated_at,
                )
                if voc_score
                else None,
                matched_insights=matched_insights,
            )
        )

    # Sort results
    if sort_by == "voc_score":
        results.sort(
            key=lambda x: x.voc_score.voc_score if x.voc_score else 0,
            reverse=True,
        )
    elif sort_by == "created_at":
        results.sort(key=lambda x: x.ticket.created_at, reverse=True)
    elif sort_by == "priority":
        priority_order = {"highest": 0, "high": 1, "medium": 2, "low": 3, "lowest": 4}
        results.sort(key=lambda x: priority_order.get(x.ticket.priority, 5))

    return results


@router.get("/jira/tickets/{ticket_key}", response_model=JiraTicketWithVOC)
async def get_ticket(ticket_key: str, db: Session = Depends(get_db)):
    """
    Get a specific Jira ticket with VOC score.

    Args:
        ticket_key: Jira ticket key (e.g., "PROD-123")
        db: Database session

    Returns:
        Ticket with VOC score
    """
    ticket = (
        db.query(JiraTicket)
        .filter(JiraTicket.jira_key == ticket_key)
        .first()
    )

    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_key} not found")

    # Get VOC score
    voc_score = (
        db.query(VOCScore)
        .filter(VOCScore.ticket_id == ticket.id)
        .first()
    )

    # Get matched insights
    matches = (
        db.query(JiraInsightMatch)
        .filter(JiraInsightMatch.ticket_id == ticket.id)
        .all()
    )

    matched_insights = []
    for match in matches:
        insight = db.query(Insight).filter(Insight.id == match.insight_id).first()
        if insight:
            matched_insights.append(
                InsightMatchResponse(
                    insight_id=str(insight.id),
                    insight_title=insight.title,
                    similarity_score=match.similarity_score,
                    confidence=match.confidence,
                    is_confirmed=match.is_confirmed,
                )
            )

    return JiraTicketWithVOC(
        ticket=JiraTicketResponse(
            id=str(ticket.id),
            jira_key=ticket.jira_key,
            title=ticket.title,
            description=ticket.description,
            status=ticket.status.value,
            priority=ticket.priority.value,
            assignee=ticket.assignee,
            reporter=ticket.reporter,
            labels=ticket.labels,
            epic_key=ticket.epic_key,
            story_points=ticket.story_points,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
        ),
        voc_score=VOCScoreResponse(
            ticket_id=str(voc_score.ticket_id),
            customer_count=voc_score.customer_count,
            total_acv=voc_score.total_acv,
            feedback_volume=voc_score.feedback_volume,
            ent_customer_count=voc_score.ent_customer_count,
            mm_customer_count=voc_score.mm_customer_count,
            smb_customer_count=voc_score.smb_customer_count,
            customer_score=voc_score.customer_score,
            acv_score=voc_score.acv_score,
            segment_score=voc_score.segment_score,
            volume_score=voc_score.volume_score,
            voc_score=voc_score.voc_score,
            recommended_priority=voc_score.recommended_priority,
            calculated_at=voc_score.calculated_at,
        )
        if voc_score
        else None,
        matched_insights=matched_insights,
    )


@router.post("/jira/tickets/{ticket_key}/calculate-voc")
async def calculate_ticket_voc(
    ticket_key: str,
    similarity_threshold: float = Query(0.6, description="Similarity threshold for insight matching"),
    db: Session = Depends(get_db),
):
    """
    Calculate VOC score for a specific ticket.

    Args:
        ticket_key: Jira ticket key
        similarity_threshold: Minimum similarity for insight matching
        db: Database session

    Returns:
        VOC score
    """
    ticket = (
        db.query(JiraTicket)
        .filter(JiraTicket.jira_key == ticket_key)
        .first()
    )

    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_key} not found")

    # Calculate VOC score
    voc_service = get_voc_scoring_service()
    score = voc_service.process_ticket(db, ticket, similarity_threshold)
    db.commit()

    logger.info(f"Calculated VOC score for {ticket_key}: {score.voc_score:.1f}")

    return VOCScoreResponse(
        ticket_id=str(score.ticket_id),
        customer_count=score.customer_count,
        total_acv=score.total_acv,
        feedback_volume=score.feedback_volume,
        ent_customer_count=score.ent_customer_count,
        mm_customer_count=score.mm_customer_count,
        smb_customer_count=score.smb_customer_count,
        customer_score=score.customer_score,
        acv_score=score.acv_score,
        segment_score=score.segment_score,
        volume_score=score.volume_score,
        voc_score=score.voc_score,
        recommended_priority=score.recommended_priority,
        calculated_at=score.calculated_at,
    )


@router.post("/jira/calculate-all-voc")
async def calculate_all_voc(
    similarity_threshold: float = Query(0.6, description="Similarity threshold for insight matching"),
    db: Session = Depends(get_db),
):
    """
    Calculate VOC scores for all Jira tickets.

    Args:
        similarity_threshold: Minimum similarity for insight matching
        db: Database session

    Returns:
        Processing statistics
    """
    voc_service = get_voc_scoring_service()
    stats = voc_service.process_all_tickets(db, similarity_threshold)

    logger.info(f"Calculated VOC scores for all tickets: {stats}")

    return {
        "message": "VOC scoring completed",
        "stats": stats,
    }


@router.post("/jira/tickets/{ticket_key}/matches/{insight_id}/confirm")
async def confirm_insight_match(
    ticket_key: str,
    insight_id: str,
    confirmed: bool = Query(..., description="true to confirm, false to reject"),
    db: Session = Depends(get_db),
):
    """
    Confirm or reject an insight match for a ticket.

    Args:
        ticket_key: Jira ticket key
        insight_id: Insight ID
        confirmed: Whether to confirm (true) or reject (false) the match
        db: Database session

    Returns:
        Updated match
    """
    ticket = (
        db.query(JiraTicket)
        .filter(JiraTicket.jira_key == ticket_key)
        .first()
    )

    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_key} not found")

    # Find match
    match = (
        db.query(JiraInsightMatch)
        .filter(
            JiraInsightMatch.ticket_id == ticket.id,
            JiraInsightMatch.insight_id == UUID(insight_id),
        )
        .first()
    )

    if not match:
        raise HTTPException(
            status_code=404,
            detail=f"No match found between {ticket_key} and insight {insight_id}",
        )

    # Update confirmation
    match.is_confirmed = 1 if confirmed else 0
    db.commit()

    logger.info(
        f"{'Confirmed' if confirmed else 'Rejected'} match between {ticket_key} and insight {insight_id}"
    )

    return {
        "message": f"Match {'confirmed' if confirmed else 'rejected'}",
        "ticket_key": ticket_key,
        "insight_id": insight_id,
        "is_confirmed": match.is_confirmed,
    }
