"""Real multimodal understanding of a capture chunk via Gemini.

This replaces the deterministic screen/transcript stubs with a single Gemini
multimodal call per chunk: the captured media (a short webm clip with video and
audio, or a single still frame) is sent to Gemini 2.5 Flash, which returns the
visible screen evidence and the spoken transcript for that window.

Every failure path degrades safely to the deterministic templates so a missing
dependency, missing credentials, or a transient model error never breaks the
capture pipeline — it just falls back to the prior behaviour.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from uuid import uuid4

from visualsprint_api.config import settings
from visualsprint_api.media_pipeline import build_screen_events
from visualsprint_api.models import (
    CaptureChunkSummary,
    ScreenEvent,
    ScreenEventKind,
    TranscriptSegment,
)
from visualsprint_api.transcript_pipeline import build_transcript_segments


_VALID_SCREEN_KINDS: set[str] = {
    "code_editor",
    "terminal",
    "diagram",
    "slide",
    "error",
    "ui_state",
}

_PROMPT = """\
You are analyzing one short screen-share clip from an engineering meeting. The
media contains the shared screen (video frames) and the spoken audio for a window
of a few seconds.

Return ONLY a JSON object — no markdown, no code fences, no prose:
{
  "screenEvents": [
    {"kind": "code_editor|terminal|diagram|slide|error|ui_state", "summary": "one factual sentence about what is visibly on screen"}
  ],
  "transcriptSegments": [
    {"speakerLabel": "Speaker 1 (or a name if stated)", "text": "verbatim spoken words"}
  ]
}

Rules:
- Describe only what is actually visible on screen; do not invent UI that is not there.
- Use "error" when a failure, stack trace, red state, or warning is visible; "terminal"
  for shells/logs; "code_editor" for source code; "diagram" for architecture/flow;
  "slide" for presentation slides; "ui_state" for app UI.
- Transcribe speech verbatim; split by speaker turn. If there is no speech, return an
  empty transcriptSegments array.
- If the screen is blank or shows nothing meaningful, return an empty screenEvents array.\
"""


def _log(msg: str) -> None:
    print(f"[api.vision] {msg}", file=sys.stderr, flush=True)


def analyze_chunk_media(
    chunk: CaptureChunkSummary,
    media_bytes: bytes | None,
    mime_type: str | None,
) -> tuple[int, list[ScreenEvent], list[TranscriptSegment], str]:
    """Return (frame_count, screen_events, transcript_segments, source).

    ``source`` is "gemini_vision" on a successful model call, otherwise
    "local_fallback" with deterministic template output.
    """

    if not media_bytes or not settings.media_vision_configured:
        return _fallback(chunk)

    try:
        parsed = _call_gemini(media_bytes, mime_type or chunk.mimeType)
    except Exception as exc:  # noqa: BLE001 - any failure must degrade safely
        _log(f"Gemini multimodal call failed ({type(exc).__name__}: {exc}); using fallback")
        return _fallback(chunk)

    screen_events = _build_screen_events(chunk, parsed.get("screenEvents", []))
    transcript_segments = _build_transcript_segments(chunk, parsed.get("transcriptSegments", []))

    if not screen_events and not transcript_segments:
        # The model saw nothing useful (blank screen, no speech). This is a real,
        # honest empty window — do NOT fabricate template content. Emit a single
        # truthful placeholder so downstream timing code still works.
        _log("Gemini returned an empty window; emitting honest no-content segment")
        return 1, [], [_no_speech_segment(chunk)], "gemini_vision"

    # Successful vision pass: never substitute stub dialogue/screen. When one
    # modality is genuinely empty (silent audio or blank screen), keep it empty
    # rather than inventing content. Downstream needs >=1 transcript segment for
    # timing, so synthesize an honest "no speech detected" marker when silent.
    if not transcript_segments:
        transcript_segments = [_no_speech_segment(chunk)]

    frame_count = max(1, len(screen_events))
    return frame_count, screen_events, transcript_segments, "gemini_vision"


def _no_speech_segment(chunk: CaptureChunkSummary) -> TranscriptSegment:
    """A truthful placeholder used when a captured window contains no speech."""
    return TranscriptSegment(
        id=f"seg_{uuid4().hex[:12]}",
        speakerLabel="System",
        text="No speech was detected in this capture window.",
        startedAt=chunk.recordedAt,
        endedAt=chunk.recordedAt + timedelta(milliseconds=chunk.durationMs),
    )


def _fallback(
    chunk: CaptureChunkSummary,
) -> tuple[int, list[ScreenEvent], list[TranscriptSegment], str]:
    frame_count, screen_events = build_screen_events(chunk)
    transcript_segments = build_transcript_segments(chunk)
    return frame_count, screen_events, transcript_segments, "local_fallback"


def _call_gemini(media_bytes: bytes, mime_type: str) -> dict:
    from google import genai
    from google.genai import types

    client = genai.Client(
        vertexai=True,
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
        http_options=types.HttpOptions(
            timeout=int(settings.media_vision_timeout_seconds * 1000)
        ),
    )
    response = client.models.generate_content(
        model=settings.vision_model,
        contents=[
            types.Part.from_bytes(data=media_bytes, mime_type=_normalize_mime(mime_type)),
            types.Part.from_text(text=_PROMPT),
        ],
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
        ),
    )
    text = (response.text or "").strip()
    _log(f"Gemini vision returned {len(text)} chars")
    return _parse_json(text)


def _normalize_mime(mime_type: str) -> str:
    base = (mime_type or "").split(";")[0].strip().lower()
    # MediaRecorder reports e.g. "video/webm;codecs=vp9,opus"; Gemini wants the base type.
    if base in {"video/webm", "video/mp4", "image/jpeg", "image/png", "image/webp"}:
        return base
    if base.startswith("video/"):
        return "video/webm"
    if base.startswith("image/"):
        return "image/jpeg"
    return "video/webm"


def _parse_json(text: str) -> dict:
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Gemini response was not a JSON object")
    return parsed


def _build_screen_events(chunk: CaptureChunkSummary, raw: object) -> list[ScreenEvent]:
    if not isinstance(raw, list):
        return []
    events: list[ScreenEvent] = []
    span = max(chunk.durationMs // (len(raw) + 1), 250) if raw else 250
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            continue
        summary = str(item.get("summary", "")).strip()
        if len(summary) < 6:
            continue
        kind = str(item.get("kind", "ui_state")).strip().lower()
        kind_value: ScreenEventKind = kind if kind in _VALID_SCREEN_KINDS else "ui_state"  # type: ignore[assignment]
        events.append(
            ScreenEvent(
                id=f"scr_{uuid4().hex[:12]}",
                kind=kind_value,
                summary=summary[:220],
                frameTimestampMs=min(chunk.durationMs, index * span),
                recordedAt=chunk.recordedAt,
            )
        )
    return events


def _build_transcript_segments(
    chunk: CaptureChunkSummary, raw: object
) -> list[TranscriptSegment]:
    if not isinstance(raw, list):
        return []
    segments: list[TranscriptSegment] = []
    count = max(len([i for i in raw if isinstance(i, dict)]), 1)
    span_ms = max(chunk.durationMs // count, 250)
    cursor: datetime = chunk.recordedAt
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        if len(text) < 8:  # TranscriptSegment.text requires min_length=8
            continue
        speaker = str(item.get("speakerLabel", "")).strip()
        if len(speaker) < 2:  # speakerLabel requires min_length=2
            speaker = f"Speaker {index}"
        ended = cursor + timedelta(milliseconds=span_ms)
        segments.append(
            TranscriptSegment(
                id=f"seg_{uuid4().hex[:12]}",
                speakerLabel=speaker[:60],
                text=text[:500],
                startedAt=cursor,
                endedAt=ended,
            )
        )
        cursor = ended
    return segments
