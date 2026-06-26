"""Media pipeline for the VisualSprint media service.

When configured, downloads the recorded chunk from GCS, samples frames with
ffmpeg, and classifies them with Gemini multimodal vision. Falls back to
deterministic templates when real services are unavailable.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from visualsprint_media.config import settings
from visualsprint_media.models import ChunkMediaRequest, ScreenEvent


SCREEN_EVENT_TEMPLATES = (
    (
        ("code_editor", "Auth configuration values are open in the editor."),
        ("error", "A release checklist warning is visible beside the auth workflow."),
    ),
    (
        ("terminal", "The terminal shows a migration validation failure in staging."),
        ("ui_state", "Deployment controls are paused while the team inspects logs."),
    ),
    (
        ("diagram", "A handoff diagram is visible for alert routing ownership."),
        ("slide", "A planning slide highlights follow-up owners for the sprint."),
    ),
)

VALID_SCREEN_KINDS = {"code_editor", "terminal", "diagram", "slide", "error", "ui_state"}


def build_screen_events(chunk: ChunkMediaRequest) -> tuple[int, list[ScreenEvent]]:
    """Produce screen events for one chunk, preferring real vision when available."""

    if settings.real_pipeline_enabled and settings.gcs_bucket and chunk.storageObjectPath:
        try:
            return _build_screen_events_from_gcs(chunk)
        except Exception:
            pass

    return _build_template_screen_events(chunk)


def _build_template_screen_events(chunk: ChunkMediaRequest) -> tuple[int, list[ScreenEvent]]:
    """Deterministic visual evidence records from chunk metadata."""

    template_index = (chunk.sequence - 1) % len(SCREEN_EVENT_TEMPLATES)
    template = SCREEN_EVENT_TEMPLATES[template_index]
    frame_count = 3 + (chunk.sequence % 3)
    events: list[ScreenEvent] = []

    for index, (kind, summary) in enumerate(template, start=1):
        events.append(
            ScreenEvent(
                id=f"scr_{uuid4().hex[:12]}",
                kind=kind,
                summary=summary,
                frameTimestampMs=min(
                    chunk.durationMs,
                    index * max(chunk.durationMs // (len(template) + 1), 250),
                ),
                recordedAt=chunk.recordedAt,
            )
        )

    return frame_count, events


def _build_screen_events_from_gcs(chunk: ChunkMediaRequest) -> tuple[int, list[ScreenEvent]]:
    """Download chunk media, sample frames, and classify them with Gemini."""

    from google.cloud import storage

    client = storage.Client(project=settings.google_cloud_project)
    bucket = client.bucket(settings.gcs_bucket)
    blob = bucket.blob(chunk.storageObjectPath)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        source_path = tmp_path / "source.webm"
        frames_dir = tmp_path / "frames"
        frames_dir.mkdir()

        blob.download_to_filename(str(source_path))
        frame_paths = _sample_frames_with_ffmpeg(source_path, frames_dir, chunk.durationMs)

        if not frame_paths:
            return _build_template_screen_events(chunk)

        frames_with_timestamps = [
            (
                path,
                int((index * chunk.durationMs) / max(len(frame_paths) - 1, 1)),
            )
            for index, path in enumerate(frame_paths)
        ]

        events = _classify_frames_with_gemini(frames_with_timestamps, chunk)
        return len(frame_paths), events


def _sample_frames_with_ffmpeg(
    source_path: Path,
    frames_dir: Path,
    duration_ms: int,
) -> list[Path]:
    """Sample evenly spaced JPEG frames from the video."""

    duration_seconds = max(duration_ms / 1000.0, 1.0)
    interval = max(settings.frame_sample_interval_seconds, 1)
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(source_path),
        "-vf",
        f"fps=1/{interval}",
        "-frames:v",
        str(min(int(duration_seconds // interval) + 1, 8)),
        str(frames_dir / "frame_%03d.jpg"),
    ]
    subprocess.run(command, check=True, capture_output=True)

    frames = sorted(frames_dir.glob("frame_*.jpg"))
    return frames


def _classify_frames_with_gemini(
    frames_with_timestamps: list[tuple[Path, int]],
    chunk: ChunkMediaRequest,
) -> list[ScreenEvent]:
    """Send sampled frames to Gemini multimodal for screen classification."""

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return _build_template_screen_events(chunk)[1]

    client = genai.Client(vertexai=True, project=settings.google_cloud_project, location=settings.google_cloud_location)

    prompt = (
        "You are reviewing frames from a screen-shared engineering meeting. "
        "For each frame, classify the screen into exactly one of these kinds: "
        "code_editor, terminal, diagram, slide, error, ui_state. "
        "Then write a concise one-sentence summary of what is visible. "
        "Return a JSON array of objects with fields: kind, summary. "
        "Only include frames that contain meaningful visual information."
    )

    contents: list[types.Content] = []
    for path, _timestamp in frames_with_timestamps:
        contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                    types.Part.from_bytes(data=path.read_bytes(), mime_type="image/jpeg"),
                ],
            )
        )

    try:
        response = client.models.generate_content(
            model=settings.gemini_vision_model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        return _parse_gemini_screen_response(
            response.text or "",
            frames_with_timestamps,
            chunk,
        )
    except Exception:
        return _build_template_screen_events(chunk)[1]


def _parse_gemini_screen_response(
    text: str,
    frames_with_timestamps: list[tuple[Path, int]],
    chunk: ChunkMediaRequest,
) -> list[ScreenEvent]:
    """Parse Gemini JSON output into ScreenEvent records."""

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return _build_template_screen_events(chunk)[1]

    if not isinstance(parsed, list):
        return _build_template_screen_events(chunk)[1]

    events: list[ScreenEvent] = []
    for index, item in enumerate(parsed):
        if not isinstance(item, dict):
            continue
        kind = item.get("kind", "ui_state")
        if kind not in VALID_SCREEN_KINDS:
            kind = "ui_state"
        summary = item.get("summary", "Screen content was detected.").strip()
        if not summary:
            summary = "Screen content was detected."
        timestamp_ms = (
            frames_with_timestamps[index][1]
            if index < len(frames_with_timestamps)
            else chunk.durationMs
        )
        events.append(
            ScreenEvent(
                id=f"scr_{uuid4().hex[:12]}",
                kind=kind,
                summary=summary,
                frameTimestampMs=timestamp_ms,
                recordedAt=chunk.recordedAt + timedelta(milliseconds=timestamp_ms),
            )
        )

    return events if events else _build_template_screen_events(chunk)[1]
