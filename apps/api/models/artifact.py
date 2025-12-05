"""Artifact model - stores tickets, PRDs, and other artifacts."""

import enum
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import JSON, Column, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from apps.api.database import Base

if TYPE_CHECKING:
    from apps.api.models.theme import Theme


class ArtifactKind(str, enum.Enum):
    """Type of artifact."""

    ticket = "ticket"
    prd = "prd"
    roadmap = "roadmap"


class Artifact(Base):
    """Product artifact (ticket, PRD, roadmap item)."""

    __tablename__ = "artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    kind = Column(Enum(ArtifactKind), nullable=False, index=True)
    external_id = Column(String(255), nullable=False, unique=True, index=True)  # e.g., JIRA-123
    title = Column(String(500), nullable=False)
    body = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True)  # Additional metadata (status, assignee, etc.)

    # Relationships
    themes = relationship("ArtifactTheme", back_populates="artifact")

    def __repr__(self) -> str:
        return f"<Artifact(id={self.id}, kind={self.kind}, external_id={self.external_id})>"


class ArtifactTheme(Base):
    """Many-to-many relationship between artifacts and themes."""

    __tablename__ = "artifact_theme"

    artifact_id = Column(
        UUID(as_uuid=True), ForeignKey("artifacts.id", ondelete="CASCADE"), primary_key=True
    )
    theme_id = Column(
        UUID(as_uuid=True), ForeignKey("themes.id", ondelete="CASCADE"), primary_key=True
    )
    coverage = Column(Float, nullable=False, default=0.0)  # How much theme is covered by artifact

    # Relationships
    artifact = relationship("Artifact", back_populates="themes")
    theme = relationship("Theme", back_populates="artifacts")

    def __repr__(self) -> str:
        return f"<ArtifactTheme(artifact_id={self.artifact_id}, theme_id={self.theme_id}, coverage={self.coverage})>"
