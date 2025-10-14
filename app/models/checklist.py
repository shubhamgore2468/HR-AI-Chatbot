from sqlalchemy import create_engine, Column, String, JSON, DateTime, Text, Boolean, Integer, ForeignKey, Index
from datetime import datetime, UTC
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from .base import Base

class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    artifact_id = Column(
        UUID(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    text = Column(Text, nullable=False)
    position = Column(Integer, nullable=False, default=0)
    is_done = Column(Boolean, nullable=False, default=False)

    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationship
    artifact = relationship("Artifact", back_populates="checklist_items")

    __table_args__ = (
        Index("ix_checklist_items_artifact_position", "artifact_id", "position"),
    )