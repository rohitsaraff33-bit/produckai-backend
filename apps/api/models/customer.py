"""Customer model - stores customer/account information."""

import enum
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import JSON, Column, Enum, Float, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from apps.api.database import Base

if TYPE_CHECKING:
    from apps.api.models.feedback import Feedback


class CustomerSegment(str, enum.Enum):
    """Customer segment classification."""

    SMB = "SMB"
    MM = "MM"
    ENT = "ENT"


class Customer(Base):
    """Customer or account that provides feedback."""

    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False, unique=True, index=True)
    acv = Column(Float, nullable=False, default=0.0)  # Annual Contract Value
    segment = Column(Enum(CustomerSegment), nullable=False, default=CustomerSegment.SMB)
    meta = Column(JSON, nullable=True)  # Additional metadata (domain, industry, etc.)

    # Relationships
    feedback = relationship("Feedback", back_populates="customer")

    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, name={self.name}, segment={self.segment}, acv={self.acv})>"
