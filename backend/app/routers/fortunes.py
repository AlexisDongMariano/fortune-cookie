"""HTTP endpoints for fortunes.

Each endpoint should be short and delegate the interesting work to
SQLAlchemy or a service. We keep things explicit rather than clever.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import SEED_EPOCH_CUTOFF, Fortune
from ..schemas import FortuneCreate, FortuneRead
from ..services.ai import generate_fortune

router = APIRouter(prefix="/api/fortunes", tags=["fortunes"])


@router.get("/random", response_model=FortuneRead)
def get_random_fortune(db: Session = Depends(get_db)):
    """Produce a fresh fortune and record it as a history row.

    Flow:
      1. Ask the AI service for a message. The service handles its own
         fallback internally, so we always get (message, source).
      2. Persist a new "draw" row with the message + source tag.
      3. Return it.
    """
    message, source = generate_fortune(db)

    drawn = Fortune(
        message=message,
        created_at=datetime.utcnow(),
        is_favorite=False,
        source=source,
    )
    db.add(drawn)
    db.commit()
    db.refresh(drawn)
    return drawn


@router.get("", response_model=list[FortuneRead])
def list_fortunes(limit: int = 50, db: Session = Depends(get_db)):
    """Most recent drawn fortunes first. Seed rows are excluded from history.

    Seeds are written with created_at = SEED_SENTINEL (year 2000). Draws use
    now(). So `created_at >= SEED_EPOCH_CUTOFF` cleanly separates the two.
    """
    stmt = (
        select(Fortune)
        .where(Fortune.created_at >= SEED_EPOCH_CUTOFF)
        .order_by(Fortune.created_at.desc())
        .limit(limit)
    )
    return db.execute(stmt).scalars().all()


@router.post("", response_model=FortuneRead, status_code=status.HTTP_201_CREATED)
def create_fortune(payload: FortuneCreate, db: Session = Depends(get_db)):
    """Manual creation endpoint — handy for adding new seed messages from the UI."""
    fortune = Fortune(message=payload.message)
    db.add(fortune)
    db.commit()
    db.refresh(fortune)
    return fortune


@router.patch("/{fortune_id}/favorite", response_model=FortuneRead)
def toggle_favorite(fortune_id: int, db: Session = Depends(get_db)):
    """Flip the is_favorite flag. Used by the heart button in the UI.

    NOTE: This endpoint is intentionally minimal — you (the learner) will
    extend it in Chapter 03 to add validation, a PUT-vs-PATCH discussion,
    and proper 404 handling tests.
    """
    fortune = db.get(Fortune, fortune_id)
    if fortune is None:
        raise HTTPException(status_code=404, detail="Fortune not found")
    fortune.is_favorite = not fortune.is_favorite
    db.commit()
    db.refresh(fortune)
    return fortune
