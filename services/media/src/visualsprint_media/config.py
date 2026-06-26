"""Configuration for the VisualSprint media service."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Mapping


def _get(environ: Mapping[str, str], key: str) -> str | None:
    value = environ.get(key)
    return value.strip() if value and value.strip() else None


def _get_int(environ: Mapping[str, str], key: str, default: int) -> int:
    value = _get(environ, key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_bool(environ: Mapping[str, str], key: str, default: bool) -> bool:
    value = _get(environ, key)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    service_name: str = "visualsprint-media"
    version: str = "0.1.0"
    selected_track: str = "elastic"
    environment: str = "development"
    google_cloud_project: str | None = None
    google_cloud_location: str | None = "us-west1"
    gcs_bucket: str | None = None
    gcs_capture_prefix: str = "capture"
    gemini_vision_model: str = "gemini-2.0-flash-001"
    frame_sample_interval_seconds: int = 2
    real_pipeline_enabled: bool = False


def build_settings(environ: Mapping[str, str] | None = None) -> Settings:
    source = os.environ if environ is None else environ
    return Settings(
        environment=source.get("VISUALSPRINT_ENV", "development"),
        selected_track=source.get("VISUALSPRINT_TRACK", "elastic"),
        google_cloud_project=_get(source, "GOOGLE_CLOUD_PROJECT"),
        google_cloud_location=_get(source, "GOOGLE_CLOUD_LOCATION") or "us-west1",
        gcs_bucket=_get(source, "GCS_BUCKET"),
        gcs_capture_prefix=_get(source, "GCS_CAPTURE_PREFIX") or "capture",
        gemini_vision_model=_get(source, "GEMINI_VISION_MODEL") or "gemini-2.0-flash-001",
        frame_sample_interval_seconds=_get_int(
            source, "VISUALSPRINT_MEDIA_FRAME_INTERVAL_SECONDS", 2
        ),
        real_pipeline_enabled=_get_bool(source, "VISUALSPRINT_MEDIA_REAL_PIPELINE_ENABLED", False),
    )


settings = build_settings()
