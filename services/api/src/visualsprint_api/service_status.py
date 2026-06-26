"""Health/status helpers for downstream deterministic services."""

from __future__ import annotations

import json
from urllib import error, request

from visualsprint_api.config import settings
from visualsprint_api.models import DownstreamServiceStatus


def get_downstream_service_statuses() -> list[DownstreamServiceStatus]:
    return [
        DownstreamServiceStatus(
            service=settings.service_name,
            kind="control_plane",
            configured=True,
            reachable=True,
            mode="local",
            baseUrl=None,
            status="ok",
            version=settings.version,
            track=settings.selected_track,
            note="The FastAPI control plane is running in the current process.",
        ),
        _probe_service(
            service_name="visualsprint-agents",
            kind="agents",
            base_url=settings.agents_service_url,
            local_note="Reasoning and summary generation will fall back to local deterministic stubs.",
        ),
        _probe_service(
            service_name="visualsprint-ingest",
            kind="ingest",
            base_url=settings.ingest_service_url,
            local_note="Transcript processing will fall back to the local deterministic pipeline.",
        ),
        _probe_service(
            service_name="visualsprint-media",
            kind="media",
            base_url=settings.media_service_url,
            local_note="Frame extraction will fall back to the local deterministic media pipeline.",
        ),
    ]


def _probe_service(
    service_name: str,
    kind: str,
    base_url: str | None,
    local_note: str,
) -> DownstreamServiceStatus:
    if not base_url:
        return DownstreamServiceStatus(
            service=service_name,
            kind=kind,
            configured=False,
            reachable=False,
            mode="fallback",
            baseUrl=None,
            status="not_configured",
            version=None,
            track=None,
            note=local_note,
        )

    health_url = f"{base_url.rstrip('/')}/api/health"
    try:
        response = request.urlopen(health_url, timeout=settings.service_request_timeout_seconds)
        payload = json.loads(response.read().decode("utf-8"))
        real_enabled = payload.get("realPipelineEnabled") is True
        note = f"{service_name} responded successfully"
        if kind in {"ingest", "media"}:
            note = (
                f"{note}; real pipeline is {'enabled' if real_enabled else 'disabled'}."
            )
        else:
            note = f"{note} to a health probe."
        return DownstreamServiceStatus(
            service=payload.get("service", service_name),
            kind=kind,
            configured=True,
            reachable=True,
            mode="remote",
            baseUrl=base_url,
            status="ok",
            version=payload.get("version"),
            track=payload.get("track"),
            note=note,
        )
    except (error.URLError, error.HTTPError, json.JSONDecodeError):
        return DownstreamServiceStatus(
            service=service_name,
            kind=kind,
            configured=True,
            reachable=False,
            mode="fallback",
            baseUrl=base_url,
            status="unreachable",
            version=None,
            track=None,
            note=local_note,
        )
