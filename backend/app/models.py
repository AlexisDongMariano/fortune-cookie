"""SQLAlchemy ORM models.

Each class maps to a database table. Keep models small and boring —
business logic belongs in routers/services, not here.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base

# Valid values for Fortune.source. We use a plain string column (not an enum
# type) so that SQLite and Postgres behave identically with zero setup.
SOURCE_AI = "ai"
SOURCE_SEED = "seed"

# Seed rows are written with this sentinel timestamp so we can distinguish
# them from real "draw" rows using only `created_at`. Any row strictly before
# SEED_EPOCH_CUTOFF is a seed; anything at or after is a user draw.
# See `seed_fortunes.py`.
from datetime import datetime as _dt  # local import to avoid namespace bleed

SEED_SENTINEL = _dt(2000, 1, 1)
SEED_EPOCH_CUTOFF = _dt(2010, 1, 1)


class Fortune(Base):
    __tablename__ = "fortunes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message: Mapped[str] = mapped_column(String(280), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # "ai"   = generated live by the LLM for this draw
    # "seed" = taken from the curated seed pool (fallback or seed row)
    source: Mapped[str] = mapped_column(String(16), default=SOURCE_SEED, nullable=False)
