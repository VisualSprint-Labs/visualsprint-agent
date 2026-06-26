"""Pydantic models for the VisualSprint media service."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ScreenEventKind = Literal[
    "code_editor",
    "terminal",
    "diagram",
    "slide",
    "error",
    "ui_state",
]


class ScreenEvent(BaseModel):
    id: str
    kind: ScreenEventKind
    summary: str = Field(min_length=6, max_length=220)
    frameTimestampMs: int = Field(ge=0)
    recordedAt: datetime


class ChunkMediaRequest(BaseModel):
    chunkId: str = Field(min_length=4, max_length=120)
    clientChunkId: str = Field(min_length=8, max_length=120)
    sequence: int = Field(ge=1)
    recordedAt: datetime
    durationMs: int = Field(ge=250, le=120_000)
    mimeType: str = Field(min_length=3, max_length=120)
    storageObjectPath: str = Field(default="", min_length=0, max_length=240)


class ChunkMediaResponse(BaseModel):
    chunkId: str
    clientChunkId: str
    frameCount: int = Field(ge=0)
    screenEvents: list[ScreenEvent] = Field(default_factory=list)
    visualEventCount: int = Field(ge=0)


class ServiceHealth(BaseModel):
    service: str
    status: Literal["ok"] = "ok"
    version: str
    track: str
    gcsBucketConfigured: bool = False
    googleCloudProjectConfigured: bool = False
    realPipelineEnabled: bool = False
