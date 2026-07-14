# Browser Capture Pipeline

This guide explains how VisualSprint captures meeting activity from the browser and turns it into backend chunk context.

## Feature Purpose

The browser capture pipeline is the bridge between a live online meeting and structured AI reasoning.

It captures:

- screen-sharing context
- microphone/system audio when available
- chunk timing
- display surface metadata
- keyframe snapshots
- recorder MIME type

The backend then turns each chunk into transcript segments, screen events, and a `ChunkInsight` payload.

## Main Frontend Files

- `apps/web/src/features/meeting-session/hooks/use-browser-capture.ts`
- `apps/web/src/lib/capture.ts`
- `apps/web/src/features/live/components/capture-guide.tsx`
- `apps/web/src/features/live/components/capture-panel.tsx`
- `apps/web/src/features/setup/components/capture-readiness.tsx`
- `apps/web/src/features/setup/components/capture-stepper.tsx`
- `apps/web/src/hooks/use-capture-support.ts`

## Main Backend Files

- `services/api/src/visualsprint_api/routes/capture.py`
- `services/api/src/visualsprint_api/repository.py`
- `services/api/src/visualsprint_api/service_clients.py`
- `services/api/src/visualsprint_api/transcript_pipeline.py`
- `services/api/src/visualsprint_api/media_pipeline.py`
- `services/api/src/visualsprint_api/vision_pipeline.py`
- `services/ingest/src/visualsprint_ingest/uploads.py`
- `services/media/src/visualsprint_media/pipeline.py`

## Capture State Model

The frontend capture phase is:

```text
idle -> requesting -> recording -> stopping -> idle
```

The backend capture session status is:

```text
idle | recording | completed
```

The chunk lifecycle is:

```text
registered -> upload_ready -> uploaded -> processing -> processed
```

These are not exactly the same thing:

- frontend phase describes the browser recorder
- backend session status describes the active capture session
- chunk lifecycle describes one recorded segment

## Important Frontend Methods

### `useCaptureSupport()`

File:

- `apps/web/src/hooks/use-capture-support.ts`

Purpose:

- checks if the browser supports screen capture
- checks whether client-side APIs are available
- lets setup UI show readiness before the user starts

Important behavior:

- uses client-only detection so server rendering does not crash
- updates when browser availability changes

### `beginBrowserCapture()`

File:

- `apps/web/src/features/meeting-session/hooks/use-browser-capture.ts`

Purpose:

- starts the real browser capture flow

High-level steps:

1. Validate that a meeting exists.
2. Validate that browser capture is supported.
3. Request screen/audio media from browser APIs.
4. Start a backend capture session.
5. Create a `MediaRecorder`.
6. Begin emitting chunks every `CHUNK_MS`.
7. Register each chunk with the API.
8. Upload or acknowledge each chunk.
9. Apply updated meeting state back to the UI.

### `stopBrowserCapture()`

Purpose:

- stops the recorder and finalizes the capture session.

Important behavior:

- stops all active media tracks
- ensures the final segment is handled
- calls backend completion when needed
- resets the frontend phase

### `buildClientChunkId(captureSessionId, sequence)`

File:

- `apps/web/src/lib/capture.ts`

Purpose:

- builds a stable client chunk ID

Why it matters:

- the frontend can safely retry chunk upload completion
- the backend can deduplicate or look up chunk context by client ID
- agent insight routes use `clientChunkId`

### `createKeyframeGrabber()`

Purpose:

- grabs a still frame from the captured video stream.

Why it matters:

- a keyframe is useful for screen context
- it gives the backend or media pipeline a visual anchor
- it can be skipped when the media is too large or unavailable

### `resolveRecorderMimeType()`

Purpose:

- selects a supported `MediaRecorder` MIME type.

Why it matters:

- browsers differ in codec support
- unsupported MIME types can make recording fail
- the backend stores MIME metadata for downstream processing

## Backend API Routes

### `POST /api/meetings/{meeting_id}/capture-sessions/start`

Implemented by:

- `start_capture_session()` in `routes/capture.py`
- `repository.start_capture_session()`

Input:

- `StartCaptureSessionRequest`

Validation:

- meeting must exist
- meeting must be `live`
- source connector must be `browser_live_capture`
- there must not already be an active recording session

Output:

- `CaptureSessionResponse`

### `POST /api/meetings/{meeting_id}/capture-sessions/chunk`

Implemented by:

- `register_capture_chunk()` in `routes/capture.py`
- `repository.register_capture_chunk()`

Input:

- `RegisterCaptureChunkRequest`

Purpose:

- creates the chunk record
- reserves an upload target
- marks the chunk as upload-ready
- returns `CaptureChunkSummary`

Important fields:

- `clientChunkId`
- `sequence`
- `recordedAt`
- `durationMs`
- `mimeType`
- `recorderMimeType`
- track metadata

### `POST /api/meetings/{meeting_id}/capture-sessions/chunk/upload-complete`

Implemented by:

- `complete_capture_chunk_upload()` in `routes/capture.py`
- `repository.complete_capture_chunk_upload()`

Purpose:

- acknowledges that the chunk media is available
- marks the chunk uploaded
- processes transcript and media context
- assembles chunk context
- prepares the chunk for reasoning

Important behavior:

- upload completion should not be tightly coupled to agent reasoning forever
- the current flow can process and then run reasoning in controlled seams
- production should keep media upload, transcript, vision, and reasoning separable

### `POST /api/meetings/{meeting_id}/capture-sessions/chunks/{client_chunk_id}/reasoning/run`

Implemented by:

- `run_chunk_reasoning()` in `routes/capture.py`
- `repository.run_chunk_reasoning()`

Purpose:

- runs reasoning for a specific uploaded/processed chunk
- useful as a cleaner production seam than making upload completion do all work

### `POST /api/meetings/{meeting_id}/capture-sessions/complete`

Implemented by:

- `complete_capture_session()` in `routes/capture.py`
- `repository.complete_capture_session()`

Purpose:

- marks the active capture session complete
- used when the frontend stops recording

## Upload Target Reservation

Upload reservation goes through:

- `reserve_chunk_upload_target()` in `services/api/src/visualsprint_api/service_clients.py`

Behavior:

- if `VISUALSPRINT_INGEST_SERVICE_URL` is configured, API calls the ingest service
- otherwise it builds a local fallback target

Local fallback target:

```text
meetings/{meeting_id}/capture-sessions/{capture_session_id}/chunks/{client_chunk_id}.webm
```

Production direction:

- ingest service should return a real signed upload target
- frontend should PUT the actual `Blob`
- backend should process from cloud storage object path

## Transcript Processing

Transcript path:

1. Chunk is uploaded or acknowledged.
2. API calls `process_transcript_chunk_with_source()`.
3. If ingest service is configured, API calls it.
4. Otherwise local fallback builds deterministic transcript segments.

Main files:

- `services/api/src/visualsprint_api/service_clients.py`
- `services/api/src/visualsprint_api/transcript_pipeline.py`
- `services/ingest/src/visualsprint_ingest/pipeline.py`

Production direction:

- Google Speech-to-Text should replace deterministic fallback for real audio.

## Screen Event Processing

Screen path:

1. Chunk is uploaded or acknowledged.
2. API calls `process_media_chunk_with_source()`.
3. If media service is configured, API calls it.
4. Otherwise local fallback creates deterministic screen events.

Main files:

- `services/api/src/visualsprint_api/media_pipeline.py`
- `services/api/src/visualsprint_api/vision_pipeline.py`
- `services/media/src/visualsprint_media/pipeline.py`

Production direction:

- Gemini multimodal vision should analyze keyframes or chunk media and produce screen events.

## Why Chunk IDs Matter

`clientChunkId` is important because:

- the browser creates chunks locally
- network calls can retry
- backend needs a stable reference
- chunk insight routes use the ID
- evidence references can point back to chunks

If this ID changes during retry, the system can duplicate chunks.

## Common Bugs To Watch For

### Capture cannot start

Likely causes:

- meeting is still draft
- browser capture APIs are unavailable
- another capture session is already recording

### Chunk upload complete returns conflict

Likely causes:

- capture session is not recording
- chunk was not registered first
- chunk is not upload-ready
- wrong `clientChunkId`

### No transcript or screen events

Possible causes:

- no media bytes were uploaded
- local fallback is being used
- ingest/media service URL is not configured
- external service failed and fallback was used

## Learning Exercise

Follow a single chunk:

1. `use-browser-capture.ts` creates a recorder chunk.
2. `buildClientChunkId()` gives it an ID.
3. `registerCaptureChunk()` posts to the API.
4. `routes/capture.py` validates the active session.
5. `repository.register_capture_chunk()` creates chunk state.
6. `reserve_chunk_upload_target()` chooses ingest or local fallback.
7. `completeCaptureChunkUpload()` acknowledges upload.
8. `repository.complete_capture_chunk_upload()` builds transcript and screen context.
9. `build_chunk_insight()` prepares agent input.
