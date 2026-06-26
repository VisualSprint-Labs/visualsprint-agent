"""FastAPI entrypoint for the VisualSprint media service."""

from __future__ import annotations

from fastapi import FastAPI

from visualsprint_media.config import settings
from visualsprint_media.models import ChunkMediaRequest, ChunkMediaResponse, ServiceHealth
from visualsprint_media.pipeline import build_screen_events


app = FastAPI(
    title="VisualSprint Media",
    version=settings.version,
    summary="Deterministic media boundary for frame extraction and visual events.",
)


@app.get("/api/health", response_model=ServiceHealth)
def get_health() -> ServiceHealth:
    return ServiceHealth(
        service=settings.service_name,
        version=settings.version,
        track=settings.selected_track,
        gcsBucketConfigured=settings.gcs_bucket is not None,
        googleCloudProjectConfigured=settings.google_cloud_project is not None,
        realPipelineEnabled=settings.real_pipeline_enabled,
    )


@app.post("/api/media/chunks/process", response_model=ChunkMediaResponse)
def process_chunk_media(payload: ChunkMediaRequest) -> ChunkMediaResponse:
    frame_count, screen_events = build_screen_events(payload)
    return ChunkMediaResponse(
        chunkId=payload.chunkId,
        clientChunkId=payload.clientChunkId,
        frameCount=frame_count,
        screenEvents=screen_events,
        visualEventCount=len(screen_events),
    )


@app.get("/")
def get_root() -> dict[str, str]:
    return {
        "name": "VisualSprint Media",
        "message": "Deterministic media services are online.",
    }
