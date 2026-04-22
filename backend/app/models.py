"""SQLAlchemy ORM models.

Each class maps to a database table. Keep models small and boring —
business logic belongs in routers/services, not here.
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Fortune(Base):
    __tablename__ = "fortunes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message: Mapped[str] = mapped_column(String(280), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
