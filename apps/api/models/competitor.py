"""Competitor and competitive intelligence models."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, Enum, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID

from apps.api.database import Base

if TYPE_CHECKING:
    pass


class CompetitorStatus(str, enum.Enum):
    """Status of competitor tracking."""

    active = "active"
    paused = "paused"
    archived = "archived"


class Competitor(Base):
    """Competitor configuration for competitive intelligence tracking."""

    __tablename__ = "competitors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False, unique=True)
    website_url = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    status = Column(Enum(CompetitorStatus), nullable=False, default=CompetitorStatus.active)

    # Research configuration
    market_scope = Column(Text, nullable=True)  # e.g., "B2B sales intelligence"
    target_personas = Column(JSON, nullable=True)  # ["SDR", "AE", "RevOps"]
    geo_segments = Column(JSON, nullable=True)  # ["NA", "EU", "SMB", "ENT"]

    # Tracking metadata
    last_researched_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Competitor(id={self.id}, name={self.name}, status={self.status})>"


class ResearchSession(Base):
    """Track competitive intelligence research sessions."""

    __tablename__ = "research_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Research parameters
    company_name = Column(String(255), nullable=False)  # Your company
    market_scope = Column(Text, nullable=False)
    target_personas = Column(JSON, nullable=False)
    geo_segments = Column(JSON, nullable=False)
    time_window_months = Column(String(50), nullable=False, default="12")

    # Session metadata
    competitors_researched = Column(JSON, nullable=False)  # List of competitor names
    insights_generated = Column(JSON, nullable=True)  # List of insight IDs
    status = Column(String(50), nullable=False, default="running")  # running, completed, failed
    error_message = Column(Text, nullable=True)

    # Citations and sources
    sources_consulted = Column(JSON, nullable=True)  # List of URLs/sources used

    # Timing
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<ResearchSession(id={self.id}, company={self.company_name}, status={self.status})>"


class CompetitiveInsightMetadata(Base):
    """Extended metadata for competitive intelligence insights."""

    __tablename__ = "competitive_insight_metadata"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    insight_id = Column(UUID(as_uuid=True), nullable=False, unique=True)  # Links to Insight

    # Competitive-specific fields
    competitor_name = Column(String(255), nullable=False)
    competitor_moves = Column(JSON, nullable=True)  # List of specific moves/releases
    evidence_count = Column(String(50), nullable=True)
    mentions_30d = Column(String(50), nullable=True)
    impacted_acv_usd = Column(String(100), nullable=True)
    est_method = Column(String(100), nullable=True)  # How ACV was estimated

    # Computed scores
    severity_weight = Column(String(50), nullable=True)
    urgency_score = Column(String(50), nullable=True)
    reach_score = Column(String(50), nullable=True)
    confidence_score = Column(String(50), nullable=True)
    effort_inverse = Column(String(50), nullable=True)

    # Citations
    citations = Column(JSON, nullable=True)  # [{"title": "...", "url": "...", "published_date": "...", "accessed_date": "..."}]

    # Research context
    research_session_id = Column(UUID(as_uuid=True), nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<CompetitiveInsightMetadata(insight_id={self.insight_id}, competitor={self.competitor_name})>"
