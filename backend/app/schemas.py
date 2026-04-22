"""Pydantic schemas = the shape of data over the wire (JSON).

Models (models.py) describe the DB. Schemas describe the API.
Keeping them separate lets you evolve either side independently.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FortuneRead(BaseModel):
    """What the API returns to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    message: str
    created_at: datetime
    is_favorite: bool


class FortuneCreate(BaseModel):
    """What the client sends to create a new fortune (admin-ish endpoint)."""

    message: str = Field(min_length=1, max_length=280)
