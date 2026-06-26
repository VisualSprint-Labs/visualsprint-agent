"""Cross-meeting knowledge search routes for the VisualSprint API.

Exposes the organizational memory (every indexed meeting outcome) as a free-text
search so teams can find past decisions, blockers, commitments, and questions.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from visualsprint_api.models import OutcomeSearchResponse
from visualsprint_api.repository import repository

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/search", response_model=OutcomeSearchResponse)
def search_knowledge(
    q: str = Query(default="", max_length=240),
    recordType: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
) -> OutcomeSearchResponse:
    record_type = recordType if recordType in {
        "decision",
        "commitment",
        "blocker",
        "open_question",
    } else None
    available, results = repository.search_outcomes(
        query=q,
        record_type=record_type,
        limit=limit,
    )
    return OutcomeSearchResponse(
        query=q,
        recordType=record_type,
        available=available,
        total=len(results),
        results=results,
    )
