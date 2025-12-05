"""Jira ticket models for VOC scoring and backlog prioritization."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from apps.api.database import Base

if TYPE_CHECKING:
    from apps.api.models.insight import Insight


class JiraTicketStatus(str, enum.Enum):
    """Jira ticket status."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CLOSED = "closed"
    BACKLOG = "backlog"


class JiraTicketPriority(str, enum.Enum):
    """Jira ticket priority."""

    LOWEST = "lowest"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    HIGHEST = "highest"


class JiraTicket(Base):
    """Jira ticket/issue for backlog prioritization."""

    __tablename__ = "jira_tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    jira_key = Column(String(50), nullable=False, unique=True, index=True)  # e.g., "PROD-123"
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(JiraTicketStatus), nullable=False, default=JiraTicketStatus.BACKLOG)
    priority = Column(Enum(JiraTicketPriority), nullable=False, default=JiraTicketPriority.MEDIUM)

    # Embedding for semantic matching
    embedding = Column(Vector(384), nullable=True)

    # Metadata
    assignee = Column(String(255), nullable=True)
    reporter = Column(String(255), nullable=True)
    labels = Column(JSON, nullable=True)  # List of labels
    epic_key = Column(String(50), nullable=True)
    story_points = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    jira_created_at = Column(DateTime, nullable=True)  # Original Jira creation date
    jira_updated_at = Column(DateTime, nullable=True)  # Original Jira update date

    # Additional metadata
    meta = Column(JSON, nullable=True)  # Store additional Jira fields

    # Relationships
    insight_matches = relationship("JiraInsightMatch", back_populates="ticket", cascade="all, delete-orphan")
    voc_scores = relationship("VOCScore", back_populates="ticket", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<JiraTicket(key={self.jira_key}, title={self.title[:50]}, status={self.status})>"


class JiraInsightMatch(Base):
    """
    Mapping between Jira tickets and insights based on semantic similarity.

    This table stores which insights are related to which Jira tickets,
    allowing us to aggregate customer feedback for VOC scoring.
    """

    __tablename__ = "jira_insight_matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("jira_tickets.id"), nullable=False)
    insight_id = Column(UUID(as_uuid=True), ForeignKey("insights.id"), nullable=False)

    # Similarity score (0-1) from semantic matching
    similarity_score = Column(Float, nullable=False)

    # Confidence level: "high" (>0.8), "medium" (0.6-0.8), "low" (<0.6)
    confidence = Column(String(20), nullable=False)

    # Manual override: PM can confirm/reject the match
    is_confirmed = Column(Integer, nullable=True)  # 1=confirmed, 0=rejected, null=pending

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    ticket = relationship("JiraTicket", back_populates="insight_matches")
    insight = relationship("Insight", back_populates="jira_matches")

    def __repr__(self) -> str:
        return f"<JiraInsightMatch(ticket={self.ticket_id}, insight={self.insight_id}, score={self.similarity_score:.2f})>"


class VOCScore(Base):
    """
    Voice of Customer (VOC) score for Jira tickets.

    Aggregates customer feedback, ACV, and other signals to help prioritize
    the Jira backlog based on actual customer demand.
    """

    __tablename__ = "voc_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("jira_tickets.id"), nullable=False, unique=True)

    # VOC Score components (0-100 scale)
    customer_count = Column(Integer, nullable=False, default=0)  # Number of unique customers
    total_acv = Column(Float, nullable=False, default=0.0)  # Total ACV of requesting customers
    feedback_volume = Column(Integer, nullable=False, default=0)  # Total feedback items

    # Segment breakdown
    ent_customer_count = Column(Integer, nullable=False, default=0)
    mm_customer_count = Column(Integer, nullable=False, default=0)
    smb_customer_count = Column(Integer, nullable=False, default=0)

    # Normalized scores (0-100)
    customer_score = Column(Float, nullable=False, default=0.0)  # Based on customer count
    acv_score = Column(Float, nullable=False, default=0.0)  # Based on total ACV
    segment_score = Column(Float, nullable=False, default=0.0)  # Weighted by segment priority
    volume_score = Column(Float, nullable=False, default=0.0)  # Based on feedback volume

    # Final VOC Score (0-100, weighted average of components)
    voc_score = Column(Float, nullable=False, default=0.0, index=True)

    # Priority recommendation: "critical", "high", "medium", "low"
    recommended_priority = Column(String(20), nullable=False, default="medium")

    # Timestamps
    calculated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    ticket = relationship("JiraTicket", back_populates="voc_scores")

    def __repr__(self) -> str:
        return f"<VOCScore(ticket={self.ticket_id}, score={self.voc_score:.1f}, customers={self.customer_count}, acv=${self.total_acv:.0f})>"
