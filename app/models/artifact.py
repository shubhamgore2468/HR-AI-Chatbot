from sqlalchemy import create_engine, Column, String, JSON, DateTime, Text, Integer
from datetime import datetime, UTC
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey, UniqueConstraint, Index
import uuid

from .base import Base

class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    type = Column(String, nullable=False, index=True)  # ArtifactType.*
    version = Column(Integer, nullable=False, default=1)  # for versioning
    title = Column(String, nullable=False, default="")
    content_md = Column(Text, nullable=False, default="")
    meta_json = Column(JSONB, nullable=False, server_default="{}")

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
    session = relationship("Session", back_populates="artifacts")
    checklist_items = relationship(
        "ChecklistItem",
        back_populates="artifact",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    job_posting = relationship(
        "JobPosting",
        back_populates="artifact",
        uselist=False,
    )

    __table_args__ = (
        # Quickly fetch latest by (session_id, type) ordering by version
        UniqueConstraint(
            "session_id", "type", "version", name="uq_artifacts_session_type_version"
        ),
        Index("ix_artifacts_session_type_version", "session_id", "type", "version"),
    )