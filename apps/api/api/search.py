"""Search endpoints."""

from typing import List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from apps.api.database import get_db
from apps.api.models import Feedback, Theme

router = APIRouter()


class SearchResult(BaseModel):
    """Search result model."""

    type: str  # "feedback" or "theme"
    id: str
    title: str
    snippet: str
    score: float

    class Config:
        from_attributes = True


@router.get("", response_model=List[SearchResult])
async def search(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
):
    """
    Unified search across feedback and themes using full-text search.

    Args:
        q: Search query
        limit: Maximum results
        db: Database session

    Returns:
        List of search results
    """
    results = []

    # Search feedback using PostgreSQL full-text search
    feedback_results = (
        db.query(Feedback, func.ts_rank(func.to_tsvector("english", Feedback.text), func.plainto_tsquery("english", q)).label("rank"))
        .filter(func.to_tsvector("english", Feedback.text).op("@@")(func.plainto_tsquery("english", q)))
        .order_by(func.ts_rank(func.to_tsvector("english", Feedback.text), func.plainto_tsquery("english", q)).desc())
        .limit(limit // 2)
        .all()
    )

    for feedback, rank in feedback_results:
        snippet = feedback.text[:200] + "..." if len(feedback.text) > 200 else feedback.text
        results.append(
            SearchResult(
                type="feedback",
                id=str(feedback.id),
                title=f"{feedback.source.value} feedback",
                snippet=snippet,
                score=float(rank),
            )
        )

    # Search themes
    theme_results = (
        db.query(Theme)
        .filter(
            or_(
                Theme.label.ilike(f"%{q}%"),
                Theme.description.ilike(f"%{q}%") if Theme.description.isnot(None) else False,
            )
        )
        .limit(limit // 2)
        .all()
    )

    for theme in theme_results:
        results.append(
            SearchResult(
                type="theme",
                id=str(theme.id),
                title=theme.label,
                snippet=theme.description or "No description",
                score=1.0,  # Simple scoring for theme matches
            )
        )

    # Sort by score
    results.sort(key=lambda x: x.score, reverse=True)

    return results[:limit]
