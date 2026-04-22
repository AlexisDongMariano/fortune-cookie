"""FastAPI application entry point.

Run locally with:
    uvicorn app.main:app --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .routers import fortunes

app = FastAPI(title="Fortune Cookie API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# For a beginner project we create tables on startup. In production you'd
# use Alembic migrations. See docs/03-feature-development.md "Stretch" section.
Base.metadata.create_all(bind=engine)

app.include_router(fortunes.router)


@app.get("/healthz", tags=["meta"])
def healthz():
    """Liveness probe. Used by Docker healthchecks and Kubernetes later."""
    return {"status": "ok"}
