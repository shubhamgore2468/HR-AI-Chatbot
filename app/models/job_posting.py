from sqlalchemy import create_engine, Column, String, JSON, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from datetime import datetime, UTC
from .base import Base


class JobPosting(Base):
    __tablename__ = "job_postings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optionally link back to the JD artifact used to publish this posting
    artifact_id = Column(
        UUID(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    role = Column(String, nullable=True, index=True)
    description = Column(Text, nullable=True)
    location = Column(String, nullable=True)

    notion_page_id = Column(String, nullable=True, unique=True, index=True)
    tags_json = Column(JSONB, nullable=False, server_default="[]")

    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    session = relationship("Session", back_populates="job_postings")
    artifact = relationship("Artifact", back_populates="job_posting")