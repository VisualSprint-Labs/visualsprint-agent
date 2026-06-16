"""Development helper routes for the VisualSprint API.

These endpoints are intended for hackathon demos and local development. They are
not meant for production use and should remain behind feature flags or removed
before a production hardening pass.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from visualsprint_api.config import settings
from visualsprint_api.models import MeetingDetailResponse
from visualsprint_api.repository import MeetingInvariantError, repository

router = APIRouter(prefix="/dev", tags=["dev"])


@router.post("/demo-seed", response_model=MeetingDetailResponse, status_code=status.HTTP_201_CREATED)
def seed_demo_meeting() -> MeetingDetailResponse:
    """Create a fully populated demo meeting for hackathon recordings.

    Bypasses the real capture pipeline and directly injects realistic transcripts,
    screen events, reasoning outputs, a final report, and action recommendations.
    """
    if not settings.demo_seed_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo seed is only available in development mode",
        )
    try:
        meeting = repository.seed_demo_meeting()
    except MeetingInvariantError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    return MeetingDetailResponse(meeting=meeting)
