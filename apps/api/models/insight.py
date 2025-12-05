"""Insight model - actionable insights synthesized from feedback."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from apps.api.database import Base

if TYPE_CHECKING:
    from apps.api.models.feedback import Feedback
    from apps.api.models.theme import Theme


class InsightCategory(str, enum.Enum):
    """Category of insight."""

    customer_feedback = "customer_feedback"  # From customer feedback clustering
    competitive_intel = "competitive_intel"  # From competitive intelligence research


class Insight(Base):
    """Actionable insight synthesized from clustered feedback or competitive research."""

    __tablename__ = "insights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    theme_id = Column(UUID(as_uuid=True), ForeignKey("themes.id"), nullable=True, index=True)  # Null for competitive insights

    # Insight category
    category = Column(
        Enum(InsightCategory),
        nullable=False,
        default=InsightCategory.customer_feedback,
        index=True,
    )

    # Core insight content
    title = Column(String(500), nullable=False)  # Concise insight title
    description = Column(Text, nullable=True)  # Detailed explanation
    impact = Column(Text, nullable=True)  # Business impact description
    recommendation = Column(Text, nullable=True)  # Actionable recommendation

    # Metrics
    severity = Column(String(50), nullable=True)  # low, medium, high, critical
    effort = Column(String(50), nullable=True)  # low, medium, high
    priority_score = Column(Integer, default=0)  # Calculated priority

    # Supporting data
    supporting_feedback_ids = Column(JSON, nullable=True)  # List of feedback IDs
    key_quotes = Column(JSON, nullable=True)  # Curated quotes from feedback
    affected_customers = Column(JSON, nullable=True)  # Customer names/segments affected

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    theme = relationship("Theme", back_populates="insights")
    jira_matches = relationship("JiraInsightMatch", back_populates="insight", cascade="all, delete-orphan")


class InsightFeedback(Base):
    """Association table linking insights to feedback items."""

    __tablename__ = "insight_feedback"

    insight_id = Column(UUID(as_uuid=True), ForeignKey("insights.id"), primary_key=True)
    feedback_id = Column(UUID(as_uuid=True), ForeignKey("feedback.id"), primary_key=True)
    relevance_score = Column(Integer, default=100)  # 0-100, how relevant this feedback is
    is_key_quote = Column(Integer, default=0)  # 1 if this is a highlighted quote

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
