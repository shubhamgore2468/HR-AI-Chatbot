# scripts/seed_db.py

from __future__ import annotations

import argparse
import random
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session as SASession

try:
    from faker import Faker
except ImportError:
    Faker = None


from app.database.database import SessionLocal, init_db
from app.models.sessions import Session as DBSession
from app.models.message import Message as DBMessage
from app.models.hiring import HiringContext as DBHiringContext
from app.models.artifact import Artifact as DBArtifact
from app.models.checklist import ChecklistItem as DBChecklistItem
from app.models.job_posting import JobPosting as DBJobPosting
from app.schemas.enums import (
    SessionStatus,
    StepName,
    Sender,
    Role,
    ArtifactType,
)

# ---------- Configurable mock pools ----------

ROLES = [
    "Software Engineer",
    "ML Engineer",
    "Backend Engineer",
    "Data Scientist",
    "DevOps Engineer",
]
SKILLS = [
    "Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes",
    "AWS", "LangChain", "LLMOps", "Redis", "CI/CD",
]
LOCATIONS = ["Remote", "Los Angeles, CA", "New York, NY", "Austin, TX", "Seattle, WA"]
TIMELINES = ["2 weeks", "4 weeks", "6 weeks"]
EXPERIENCE = ["Junior", "Mid", "Senior"]

CHECKLIST = [
    "Post job description on job boards",
    "Screen resumes (Week 1)",
    "Conduct phone interviews (Week 2)",
    "Technical interviews (Week 3)",
    "Final interviews & offer (Week 4)",
]

# ---------- Helpers ----------

def maybe_faker():
    if Faker is None:
        return None
    return Faker()

def reset_db(db: SASession):
    """
    Danger: wipes all data in child tables and sessions (order matters).
    Works for Postgres; adjust for your DB if needed.
    """
    # Disable FK checks if needed (for other DBs). Postgres handles CASCADE on delete.
    # Here we issue explicit deletes to preserve sequences.
    db.execute(text("DELETE FROM job_postings;"))
    db.execute(text("DELETE FROM checklist_items;"))
    db.execute(text("DELETE FROM artifacts;"))
    db.execute(text("DELETE FROM messages;"))
    db.execute(text("DELETE FROM hiring_contexts;"))
    db.execute(text("DELETE FROM sessions;"))
    db.commit()

def make_hiring_context(session_id: uuid4) -> DBHiringContext:
    role = random.choice(ROLES)
    skills = random.sample(SKILLS, k=random.randint(3, 6))
    ctx = DBHiringContext(
        session_id=session_id,
        primary_role=role,
        budget=f"${random.randint(100, 200)}k",
        timeline=random.choice(TIMELINES),
        location=random.choice(LOCATIONS),
        experience_level=random.choice(EXPERIENCE),
        skills_json=skills,
        extras_json={"headcount": random.choice([1, 2, 3])},
    )
    return ctx

def make_conversation(db: SASession, session_id, num_pairs: int = 3, faker: Faker | None = None):
    """
    Creates num_pairs of (user, assistant) messages for a session.
    """
    for i in range(num_pairs):
        user_text = (
            faker.sentence(nb_words=10) if faker else f"User question #{i+1}: Tell me more about the role."
        )
        db.add(DBMessage(
            session_id=session_id,
            sender=Sender.user.value,
            role=Role.user.value,
            content=user_text,
            meta_json={"turn": i * 2 + 1},
        ))
        ai_text = (
            faker.paragraph(nb_sentences=2) if faker else f"Assistant reply #{i+1}: Here are the details..."
        )
        db.add(DBMessage(
            session_id=session_id,
            sender=Sender.agent.value,
            role=Role.assistant.value,
            content=ai_text,
            meta_json={"turn": i * 2 + 2},
        ))

def make_artifacts_with_plan(db: SASession, session_id, role: str):
    """
    Creates a JD artifact (v1) and a hiring plan artifact (v1) with checklist items.
    Returns (jd_artifact, plan_artifact).
    """
    jd_md = f"""# Job Description: {role}

## About the Role
We're looking for a {role} to join our team.

## Required Skills
- {", ".join(random.sample(SKILLS, k=5))}
"""
    jd = DBArtifact(
        session_id=session_id,
        type=ArtifactType.job_description.value,
        version=1,
        title=f"Job Description: {role}",
        content_md=jd_md,
        meta_json={"generated_by": "seed_script"},
    )
    db.add(jd)
    db.flush()  # to get jd.id

    plan_md = f"""# Hiring Plan
## Timeline: {random.choice(TIMELINES)}

## Checklist
""" + "\n".join([f"{i+1}. [ ] {item}" for i, item in enumerate(CHECKLIST)])

    plan = DBArtifact(
        session_id=session_id,
        type=ArtifactType.hiring_plan.value,
        version=1,
        title=f"Hiring Plan: {role}",
        content_md=plan_md,
        meta_json={"generated_by": "seed_script"},
    )
    db.add(plan)
    db.flush()

    # Checklist items (actionable)
    for pos, text_item in enumerate(CHECKLIST):
        db.add(DBChecklistItem(
            artifact_id=plan.id,
            text=text_item,
            position=pos,
            is_done=False,
        ))

    return jd, plan

def maybe_make_job_posting(db: SASession, session_id, jd_artifact: DBArtifact, faker: Faker | None = None):
    """
    Optionally create a job posting tied to the JD artifact.
    """
    notion_id = str(uuid4())  # pretend we created a Notion page
    jp = DBJobPosting(
        session_id=session_id,
        artifact_id=jd_artifact.id,
        role=jd_artifact.title.replace("Job Description: ", ""),
        description=jd_artifact.content_md,
        location=random.choice(LOCATIONS),
        notion_page_id=notion_id,
        tags_json=random.sample(SKILLS, k=3),
    )
    db.add(jp)

# ---------- Main seeding routine ----------

def seed(sessions: int = 3, messages: int = 3, reset: bool = False):
    """
    Creates `sessions` number of Sessions.
    For each, creates:
      - HiringContext
      - `messages` user/assistant pairs
      - JD (v1) artifact + Hiring Plan (v1) artifact
      - Checklist items for the plan
      - A JobPosting linked to the JD
    """
    fake = maybe_faker()

    with SessionLocal() as db:
        # create tables for dev if needed (prefer Alembic in real env)
        init_db()

        if reset:
            print("⚠️  Resetting database tables...")
            reset_db(db)

        for n in range(sessions):
            sid = uuid4()
            sess = DBSession(
                id=sid,
                status=SessionStatus.active.value,
                current_step=StepName.plan_created.value,
                context_json={"seed_batch": n},
            )
            db.add(sess)
            db.flush()

            # Hiring context
            ctx = make_hiring_context(sid)
            db.add(ctx)
            db.flush()

            # Conversation
            make_conversation(db, sid, num_pairs=messages, faker=fake)

            # Artifacts + plan checklist
            jd, plan = make_artifacts_with_plan(db, sid, role=ctx.primary_role or "Software Engineer")

            # Optional job posting
            maybe_make_job_posting(db, sid, jd_artifact=jd, faker=fake)

        db.commit()
        print(f"✅ Seeded {sessions} sessions × {messages} message pairs each.")

# ---------- CLI ----------

def main():
    parser = argparse.ArgumentParser(description="Seed the HR Agent database with mock data.")
    parser.add_argument("--sessions", type=int, default=3, help="How many sessions to create")
    parser.add_argument("--messages", type=int, default=3, help="User/assistant message pairs per session")
    parser.add_argument("--reset", action="store_true", help="Wipe tables before seeding")
    args = parser.parse_args()

    seed(sessions=args.sessions, messages=args.messages, reset=args.reset)

if __name__ == "__main__":
    main()
