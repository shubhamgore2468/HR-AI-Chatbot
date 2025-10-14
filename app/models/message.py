from sqlalchemy import create_engine, Column, String, JSON, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from enum import Enum
from sqlalchemy import Index
from .base import Base


class Sender(str, Enum):
    user = "user"
    agent = "agent"
    system = "system"


class Role(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"

class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sender = Column(String, nullable=False, default=Sender.user.value)
    role = Column(String, nullable=False, default=Role.user.value)

    content = Column(Text, nullable=False, default="")
    meta_json = Column(JSONB, nullable=False, server_default="{}")

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationship
    session = relationship("app.models.sessions.Session", back_populates="messages")

    __table_args__ = (
        Index("ix_messages_session_created_at", "session_id", "created_at"),
    )