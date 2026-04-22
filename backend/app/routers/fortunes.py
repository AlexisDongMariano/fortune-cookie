"""HTTP endpoints for fortunes.

Each endpoint should be short and delegate the interesting work to
SQLAlchemy. We keep things explicit rather than clever.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Fortune
from ..schemas import FortuneCreate, FortuneRead

router = APIRouter(prefix="/api/fortunes", tags=["fortunes"])


@router.get("/random", response_model=FortuneRead)
def get_random_fortune(db: Session = Depends(get_db)):
    """Return a random fortune and log it as 'drawn' by inserting a history row.

    Design choice: we store every draw as a new row so the history shows
    a timeline of *when* each message was revealed, not just the master list.
    """
    # Seed rows use low IDs (<=1000) so we can pick randomly from only the
    # curated pool — not from the history of previously-drawn fortunes.
    seed_stmt = select(Fortune).where(Fortune.id <= 1000).order_by(func.random()).limit(1)
    seed = db.execute(seed_stmt).scalar_one_or_none()
    if seed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No fortunes seeded. Run `python seed_fortunes.py` first.",
        )

    # Record the draw as a new history row (a separate entity conceptually,
    # but for simplicity we reuse the same table with created_at=now).
    drawn = Fortune(message=seed.message, created_at=datetime.utcnow(), is_favorite=False)
    db.add(drawn)
    db.commit()
    db.refresh(drawn)
    return drawn


@router.get("", response_model=list[FortuneRead])
def list_fortunes(limit: int = 50, db: Session = Depends(get_db)):
    """Most recent drawn fortunes first. Seed rows are excluded from history."""
    stmt = (
        select(Fortune)
        .where(Fortune.id > 1000)
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
