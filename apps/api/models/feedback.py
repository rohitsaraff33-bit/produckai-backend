"""Feedback model - stores raw feedback from various sources."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Column, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from apps.api.database import Base

if TYPE_CHECKING:
    from apps.api.models.customer import Customer
    from apps.api.models.theme import Theme


class FeedbackSource(str, enum.Enum):
    """Source of feedback."""

    slack = "slack"
    jira = "jira"
    linear = "linear"
    upload = "upload"
    gdoc = "gdoc"
    zoom = "zoom"


class Feedback(Base):
    """Raw feedback from various sources."""

    __tablename__ = "feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    source = Column(Enum(FeedbackSource), nullable=False, index=True)
    source_id = Column(String(255), nullable=False)  # External ID (e.g., Slack message ID)
    account = Column(String(255), nullable=True)  # Account/company identifier
    text = Column(Text, nullable=False)
    embedding = Column(Vector(384), nullable=True)  # Will be populated async
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    meta = Column(JSON, nullable=True)  # Additional metadata (author, channel, etc.)

    # New columns for Google Docs and Zoom
    doc_url = Column(Text, nullable=True)  # webViewLink for GDocs or recording URL for Zoom
    speaker = Column(Text, nullable=True)  # Speaker name/tag for Zoom transcripts
    started_at = Column(DateTime, nullable=True)  # Segment start time for Zoom
    ended_at = Column(DateTime, nullable=True)  # Segment end time for Zoom

    # Relationships
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    customer = relationship("Customer", back_populates="feedback")
    themes = relationship("FeedbackTheme", back_populates="feedback")

    def __repr__(self) -> str:
        return f"<Feedback(id={self.id}, source={self.source}, text={self.text[:50]}...)>"


class FeedbackTheme(Base):
    """Many-to-many relationship between feedback and themes."""

    __tablename__ = "feedback_theme"

    feedback_id = Column(
        UUID(as_uuid=True), ForeignKey("feedback.id", ondelete="CASCADE"), primary_key=True
    )
    theme_id = Column(
        UUID(as_uuid=True), ForeignKey("themes.id", ondelete="CASCADE"), primary_key=True
    )
    confidence = Column(Float, nullable=False, default=1.0)  # Clustering confidence

    # Relationships
    feedback = relationship("Feedback", back_populates="themes")
    theme = relationship("Theme", back_populates="feedback_items")

    def __repr__(self) -> str:
        return f"<FeedbackTheme(feedback_id={self.feedback_id}, theme_id={self.theme_id}, confidence={self.confidence})>"
