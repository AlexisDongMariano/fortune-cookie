"""Database engine + session factory.

SQLAlchemy pattern:
  - One `engine` per process.
  - One `SessionLocal` per request (via the `get_db` FastAPI dependency).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def get_db():
    """FastAPI dependency. Yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
