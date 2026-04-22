"""Seed the database with a starter pool of fortune messages.

Run once after installing dependencies:
    python seed_fortunes.py

Seed rows are inserted with explicit IDs 1..N so the API can tell them
apart from "drawn" (history) rows. This is a deliberate simplification
for the MVP — in Chapter 03 you'll refactor this into a separate
`fortune_messages` vs `fortune_draws` two-table design.
"""
from datetime import datetime

from app.database import Base, SessionLocal, engine
from app.models import SOURCE_SEED, Fortune

SEED_MESSAGES = [
    "A fresh start will put you on your way.",
    "A journey of a thousand miles begins with a single step.",
    "An unexpected opportunity is about to appear.",
    "Be the reason someone smiles today.",
    "Courage is the first step toward confidence.",
    "Do one thing every day that scares you, only a little.",
    "Every solved problem becomes a new skill.",
    "Good things happen to those who ship.",
    "Hard work will be rewarded soon.",
    "If you can dream it, you can deploy it.",
    "Learning is a superpower. Keep going.",
    "Persistence compounds faster than talent.",
    "Small consistent effort beats big bursts.",
    "The best code is the code you didn't have to write.",
    "The best time to start was yesterday. The second best is now.",
    "Trust the process and review the logs.",
    "You are closer than you think.",
    "Your next commit will be your best one.",
    "Fortune favors the person who reads the docs.",
    "Today is a good day to learn something new.",
]


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(Fortune).filter(Fortune.id <= 1000).count()
        if existing >= len(SEED_MESSAGES):
            print(f"Already seeded ({existing} seed rows). Nothing to do.")
            return

        # Use deterministic small IDs for seed rows so the /random endpoint
        # can select only from them via `id <= 1000`.
        for idx, message in enumerate(SEED_MESSAGES, start=1):
            if db.get(Fortune, idx) is None:
                db.add(
                    Fortune(
                        id=idx,
                        message=message,
                        created_at=datetime(2000, 1, 1),
                        source=SOURCE_SEED,
                    )
                )
        db.commit()
        print(f"Seeded {len(SEED_MESSAGES)} fortunes.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
