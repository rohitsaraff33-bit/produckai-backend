"""Artifact (ticket) endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.database import get_db
from apps.api.models import Artifact, ArtifactKind

router = APIRouter()


class TicketScoreResponse(BaseModel):
    """Ticket ThemeScore response."""

    ticket_key: str
    themes: List[dict]
    top_quotes: List[dict]
    overall_score: float


class DraftPRDRequest(BaseModel):
    """Request to draft PRD."""

    pass  # No additional fields needed


class DraftPRDResponse(BaseModel):
    """Draft PRD response."""

    ticket_key: str
    prd_markdown: str


@router.get("/{ticket_key}/score", response_model=TicketScoreResponse)
async def get_ticket_score(
    ticket_key: str,
    db: Session = Depends(get_db),
):
    """
    Get ThemeScore for a Jira ticket.

    Args:
        ticket_key: Jira ticket key (e.g., PROD-123)
        db: Database session

    Returns:
        Ticket score with themes and quotes
    """
    # Look up artifact
    artifact = (
        db.query(Artifact)
        .filter(Artifact.external_id == ticket_key, Artifact.kind == ArtifactKind.ticket)
        .first()
    )

    if not artifact:
        # Return empty result if not found (ticket not yet ingested)
        return TicketScoreResponse(
            ticket_key=ticket_key,
            themes=[],
            top_quotes=[],
            overall_score=0.0,
        )

    # Get related themes
    from apps.api.models import ArtifactTheme, FeedbackTheme, Theme, ThemeMetrics

    related_themes = (
        db.query(Theme, ArtifactTheme.coverage, ThemeMetrics.score)
        .join(ArtifactTheme, Theme.id == ArtifactTheme.theme_id)
        .join(ThemeMetrics, Theme.id == ThemeMetrics.theme_id, isouter=True)
        .filter(ArtifactTheme.artifact_id == artifact.id)
        .order_by(ThemeMetrics.score.desc() if ThemeMetrics.score else Theme.created_at.desc())
        .limit(3)
        .all()
    )

    themes = [
        {
            "id": str(theme.id),
            "label": theme.label,
            "score": score or 0.0,
            "coverage": coverage,
        }
        for theme, coverage, score in related_themes
    ]

    # Get top quotes from these themes
    from apps.api.models import Feedback

    quotes = []
    for theme, _, _ in related_themes[:1]:  # Just from top theme
        feedback_items = (
            db.query(Feedback)
            .join(FeedbackTheme, Feedback.id == FeedbackTheme.feedback_id)
            .filter(FeedbackTheme.theme_id == theme.id)
            .limit(3)
            .all()
        )

        for f in feedback_items:
            quotes.append(
                {
                    "text": f.text[:200] + "..." if len(f.text) > 200 else f.text,
                    "source": f.source.value,
                    "created_at": f.created_at.isoformat(),
                }
            )

    overall_score = sum(t["score"] * t["coverage"] for t in themes) / len(themes) if themes else 0.0

    return TicketScoreResponse(
        ticket_key=ticket_key,
        themes=themes,
        top_quotes=quotes,
        overall_score=overall_score,
    )


@router.post("/{ticket_key}/draft_prd", response_model=DraftPRDResponse)
async def draft_prd(
    ticket_key: str,
    db: Session = Depends(get_db),
):
    """
    Generate a PRD outline for a ticket based on related themes.

    Args:
        ticket_key: Jira ticket key
        db: Database session

    Returns:
        PRD markdown with citations
    """
    # Get ticket score first
    score_data = await get_ticket_score(ticket_key, db)

    # Generate simple PRD outline
    prd_md = f"""# PRD: {ticket_key}

## Problem Statement
This ticket addresses {len(score_data.themes)} key themes identified from customer feedback.

## Related Themes
"""

    for theme in score_data.themes:
        prd_md += f"\n### {theme['label']} (Score: {theme['score']:.2f})\n"

    prd_md += "\n## Customer Quotes\n"
    for i, quote in enumerate(score_data.top_quotes, 1):
        prd_md += f"\n{i}. \"{quote['text']}\" - {quote['source']} ({quote['created_at']})\n"

    prd_md += "\n## Next Steps\n- Define requirements\n- Create technical design\n- Estimate effort\n"

    return DraftPRDResponse(
        ticket_key=ticket_key,
        prd_markdown=prd_md,
    )
