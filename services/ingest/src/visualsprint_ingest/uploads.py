"""Upload reservation helpers for the VisualSprint ingest service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from visualsprint_ingest.config import settings
from visualsprint_ingest.models import ChunkUploadReservationRequest, ChunkUploadTarget


def _build_local_upload_target(
    payload: ChunkUploadReservationRequest,
) -> ChunkUploadTarget:
    object_path = (
        f"meetings/{payload.meetingId}/capture-sessions/"
        f"{payload.captureSessionId}/chunks/{payload.clientChunkId}.webm"
    )
    return ChunkUploadTarget(
        objectPath=object_path,
        requiredHeaders={
            "Content-Type": payload.mimeType,
            "X-VisualSprint-Chunk-Id": payload.clientChunkId,
        },
    )


def reserve_chunk_upload_target(payload: ChunkUploadReservationRequest) -> ChunkUploadTarget:
    """Build an upload contract for a capture chunk.

    When GCS is configured, returns a real v4 signed PUT URL. Otherwise returns a
    local deterministic contract so development can proceed without GCP.
    """

    local_target = _build_local_upload_target(payload)
    if not settings.gcs_bucket or not settings.google_cloud_project:
        return local_target

    try:
        from google.cloud import storage

        client = storage.Client(project=settings.google_cloud_project)
        bucket = client.bucket(settings.gcs_bucket)
        blob = bucket.blob(local_target.objectPath)

        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=settings.gcs_signed_url_ttl_seconds
        )
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=expires_at,
            method="PUT",
            content_type=payload.mimeType,
        )

        return ChunkUploadTarget(
            objectPath=local_target.objectPath,
            signedUrl=signed_url,
            requiredHeaders={
                "Content-Type": payload.mimeType,
                "X-VisualSprint-Chunk-Id": payload.clientChunkId,
            },
            expiresAt=expires_at,
        )
    except Exception:
        # Fall back to the deterministic contract if GCS signing fails for any
        # reason, so the service stays usable in environments without credentials.
        return local_target
