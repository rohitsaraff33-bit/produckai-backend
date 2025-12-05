"""Theme model - clustered feedback themes."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from apps.api.database import Base

if TYPE_CHECKING:
    from apps.api.models.feedback import FeedbackTheme


class Theme(Base):
    """Clustered theme from feedback."""

    __tablename__ = "themes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    label = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    centroid = Column(Vector(384), nullable=True)  # Cluster centroid embedding
    version = Column(Integer, nullable=False, default=1)  # For tracking re-clustering
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)

    # Relationships
    feedback_items = relationship("FeedbackTheme", back_populates="theme")
    metrics = relationship("ThemeMetrics", back_populates="theme", uselist=False)
    artifacts = relationship("ArtifactTheme", back_populates="theme")
    insights = relationship("Insight", back_populates="theme")

    def __repr__(self) -> str:
        return f"<Theme(id={self.id}, label={self.label}, version={self.version})>"


class ThemeMetrics(Base):
    """Computed metrics and scores for themes."""

    __tablename__ = "theme_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    theme_id = Column(UUID(as_uuid=True), ForeignKey("themes.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Frequency metrics
    freq_30d = Column(Integer, nullable=False, default=0)
    freq_90d = Column(Integer, nullable=False, default=0)

    # ACV metrics
    acv_sum = Column(Float, nullable=False, default=0.0)

    # Sentiment
    sentiment = Column(Float, nullable=False, default=0.0)  # Average sentiment (-1 to 1)

    # Trend
    trend = Column(Float, nullable=False, default=0.0)  # Linear regression slope

    # Duplicate penalty
    dup_penalty = Column(Float, nullable=False, default=0.0)

    # Final ThemeScore
    score = Column(Float, nullable=False, default=0.0, index=True)

    # Relationships
    theme = relationship("Theme", back_populates="metrics")

    def __repr__(self) -> str:
        return f"<ThemeMetrics(theme_id={self.theme_id}, score={self.score})>"
