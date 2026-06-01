"""HTTP status endpoint for the latest emotion service state."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime

from app.state import get_state_store

router = APIRouter(tags=["emotion"])


class StatusResponse(BaseModel):
    """Latest state exposed by the emotion service."""

    emotion: str
    confidence: float
    redness_score: float
    redness_level: str
    redness_reliable: bool
    inactivity_seconds: int
    last_updated: datetime


@router.get("/status", response_model=StatusResponse)
@router.get("/status/emotion", response_model=StatusResponse)
def get_status() -> StatusResponse:
    """Return the latest in-memory emotion state."""
    snapshot = get_state_store().snapshot()
    return StatusResponse(**snapshot.as_dict())