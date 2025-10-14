from sqlalchemy.ext.declarative import declarative_base
from app.models.base import Base  # Import Base from your models module
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/mydb")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    # import app.models
    Base.metadata.create_all(bind=engine)


def get_db():
    """Yield a DB session; remember to close after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()