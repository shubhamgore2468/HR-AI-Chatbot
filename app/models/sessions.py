from sqlalchemy import create_engine, Column, String, JSON, DateTime, Text
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base
import uuid
from enum import Enum



class SessionStatus(str, Enum):
    active = "active"
    archived = "archived"
    error = "error"


class StepName(str, Enum):
    start = "start"
    jd_created = "jd_created"
    plan_created = "plan_created"
    posted_to_notion = "posted_to_notion"
    completed = "completed"


class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String, nullable=False, default=SessionStatus.active.value, index=True)
    current_step = Column(String, nullable=False, default=StepName.start.value, index=True)

    # Keep a small flexible bag for debugging inputs/flags
    context_json = Column(JSONB, nullable=False, server_default="{}")

    created_at = Column(DateTime(timezone=True),nullable=False,server_default=func.now(),)
    updated_at = Column(DateTime(timezone=True),nullable=False,server_default=func.now(),onupdate=func.now())

    # Relationships
    messages = relationship("app.models.message.Message", back_populates="session", cascade="all, delete-orphan", passive_deletes=True,)
    artifacts = relationship("Artifact",back_populates="session",cascade="all, delete-orphan",passive_deletes=True,)
    job_postings = relationship("JobPosting",back_populates="session",cascade="all, delete-orphan",passive_deletes=True,)
    hiring_context = relationship("HiringContext",back_populates="session",uselist=False,cascade="all, delete-orphan",passive_deletes=True,)
