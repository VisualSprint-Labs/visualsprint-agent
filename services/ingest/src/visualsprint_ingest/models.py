"""Pydantic models for the VisualSprint ingest service."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChunkUploadReservationRequest(BaseModel):
    meetingId: str = Field(min_length=4, max_length=120)
    captureSessionId: str = Field(min_length=4, max_length=120)
    clientChunkId: str = Field(min_length=8, max_length=120)
    sequence: int = Field(ge=1)
    mimeType: str = Field(min_length=3, max_length=120)


class ChunkUploadTarget(BaseModel):
    method: Literal["PUT"] = "PUT"
    objectPath: str = Field(min_length=8, max_length=240)
    signedUrl: str | None = None
    requiredHeaders: dict[str, str] = Field(default_factory=dict)
    expiresAt: datetime | None = None


class ChunkUploadReservationResponse(BaseModel):
    clientChunkId: str
    uploadTarget: ChunkUploadTarget


class TranscriptSegment(BaseModel):
    id: str
    speakerLabel: str = Field(min_length=2, max_length=60)
    startedAt: datetime
    endedAt: datetime
    text: str = Field(min_length=8, max_length=500)


class ChunkTranscriptRequest(BaseModel):
    chunkId: str = Field(min_length=4, max_length=120)
    clientChunkId: str = Field(min_length=8, max_length=120)
    sequence: int = Field(ge=1)
    recordedAt: datetime
    durationMs: int = Field(ge=250, le=120_000)
    mimeType: str = Field(min_length=3, max_length=120)
    storageObjectPath: str = Field(default="", min_length=0, max_length=240)


class ChunkTranscriptResponse(BaseModel):
    chunkId: str
    clientChunkId: str
    transcriptSegments: list[TranscriptSegment] = Field(default_factory=list)
    transcriptSegmentCount: int = Field(ge=0)


class ServiceHealth(BaseModel):
    service: str
    status: Literal["ok"] = "ok"
    version: str
    track: str
    gcsBucketConfigured: bool = False
    googleCloudProjectConfigured: bool = False
    realPipelineEnabled: bool = False
