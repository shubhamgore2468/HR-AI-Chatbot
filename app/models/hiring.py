from sqlalchemy import create_engine, Column, String, JSON, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from sqlalchemy import ForeignKey
from .base import Base


class HiringContext(Base):
    __tablename__ = "hiring_contexts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Structured inputs
    primary_role = Column(String, nullable=True, index=True)
    budget = Column(String, nullable=True)
    timeline = Column(String, nullable=True)
    location = Column(String, nullable=True)
    experience_level = Column(String, nullable=True)

    # Flexible fields
    skills_json = Column(JSONB, nullable=False, server_default="[]")
    extras_json = Column(JSONB, nullable=False, server_default="{}")

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True),nullable=False,server_default=func.now(),onupdate=func.now(),)

    # Relationship
    session = relationship("Session", back_populates="hiring_context")