# Meeting Lifecycle

This guide explains how a meeting moves through VisualSprint from creation to final report.

## Feature Purpose

The meeting lifecycle gives every capture chunk, transcript segment, screen event, decision, commitment, blocker, memory match, report, and action recommendation a stable parent object.

Without the meeting lifecycle, the product would only have loose media chunks and agent responses. The lifecycle turns those into a coherent session.

## Main User Flow

1. User opens the app.
2. User creates a draft meeting.
3. User starts the meeting.
4. User starts browser capture.
5. Chunks are registered and processed while the meeting is live.
6. User ends the meeting.
7. API finalizes a report.
8. User reviews actions and knowledge search later.

## Frontend Files

Important files:

- `apps/web/src/app/meetings/page.tsx`: meetings route.
- `apps/web/src/app/meetings/new/page.tsx`: meeting setup route.
- `apps/web/src/app/meetings/[id]/page.tsx`: meeting workspace route.
- `apps/web/src/features/workspace/meeting-workspace.tsx`: chooses setup, live, report, actions, or dev panels.
- `apps/web/src/features/setup/meeting-setup-page.tsx`: creation and setup UI.
- `apps/web/src/features/meetings/meetings-list-page.tsx`: meeting list UI.
- `apps/web/src/features/meeting-session/context/meeting-session-provider.tsx`: central client state and API actions.
- `apps/web/src/lib/api.ts`: frontend HTTP methods.

## Backend Files

Important files:

- `services/api/src/visualsprint_api/routes/meetings.py`: HTTP routes.
- `services/api/src/visualsprint_api/repository.py`: lifecycle rules and stored state.
- `services/api/src/visualsprint_api/models.py`: Pydantic models.
- `packages/contracts/src/domain.ts`: TypeScript contracts.

## Main Data Models

### `MeetingSummary`

Used for list views. It contains lightweight meeting information such as:

- `id`
- `title`
- `participantCount`
- `status`
- `sourceConnector`
- `primaryTrack`
- timestamps
- `metrics`

### `MeetingDetail`

Used for full pages and live state. It extends `MeetingSummary` and adds:

- `activeCaptureSession`
- `recentCaptureChunks`
- `latestEvents`
- `transcriptSegments`
- `screenEvents`
- `decisions`
- `commitments`
- `blockers`
- `memoryMatches`
- `openQuestions`
- `finalReport`
- `actionRecommendations`

### `MeetingMetrics`

This keeps the UI fast because the frontend can render counters without scanning every array.

Typical metrics:

- capture chunks count
- transcript segment count
- screen event count
- decision count
- commitment count
- blocker count
- memory match count
- open question count
- action recommendation count

## API Routes

### `GET /api/meetings`

Implemented by:

- `list_meetings()` in `routes/meetings.py`
- `repository.list_meetings()`

Purpose:

- returns all meeting summaries
- powers meeting list and setup sidebar

### `POST /api/meetings`

Implemented by:

- `create_meeting()` in `routes/meetings.py`
- `repository.create_meeting(payload)`

Input:

- `CreateMeetingRequest`

Important fields:

- `title`
- `participantCount`
- `sourceConnector`
- `notes`

Output:

- `CreateMeetingResponse`
- includes a full `MeetingDetail`

Why it matters:

- creates a stable `meeting.id`
- initializes metrics
- prepares the meeting for capture

### `GET /api/meetings/{meeting_id}`

Implemented by:

- `get_meeting()` in `routes/meetings.py`
- `repository.get_meeting(meeting_id)`

Purpose:

- loads the full meeting detail for setup, live, report, and actions pages

### `POST /api/meetings/{meeting_id}/start`

Implemented by:

- `start_meeting()` in `routes/meetings.py`
- `repository.start_meeting(meeting_id)`

Purpose:

- moves a meeting from `draft` to `live`
- allows capture to start

Important behavior:

- capture routes require the meeting to be live
- the live dashboard depends on this status

### `POST /api/meetings/{meeting_id}/end`

Implemented by:

- `end_meeting()` in `routes/meetings.py`
- `repository.end_meeting(meeting_id)`

Purpose:

- moves a meeting from `live` to `ended`
- prepares the meeting for final report generation

### `GET /api/meetings/{meeting_id}/state`

Implemented by:

- `get_meeting_state()` in `routes/meetings.py`
- `repository.get_meeting_state(meeting_id)`

Purpose:

- returns a compact `MeetingStateSnapshot`
- this is the type of context agents should reason against instead of raw full state

### `GET /api/meetings/{meeting_id}/events`

Implemented by:

- `stream_meeting_events()` in `routes/meetings.py`

Purpose:

- Server-Sent Events stream for live UI updates
- sends `meeting.updated` whenever the repository revision changes
- also sends keepalive comments

How it works:

1. The route checks that the meeting exists.
2. It reads the repository revision.
3. It loops forever while the meeting exists.
4. If the revision changed, it serializes `MeetingStreamEvent`.
5. It yields an SSE event.
6. It sleeps for one second between checks.

Frontend hook:

- `apps/web/src/hooks/use-meeting-stream.ts`

## Frontend State Provider

The most important frontend lifecycle file is:

- `apps/web/src/features/meeting-session/context/meeting-session-provider.tsx`

It provides:

- current meeting ID
- current `MeetingDetail`
- meeting list
- draft creation state
- busy/error state
- stream status
- capture state
- final report
- chunk insight
- summary packet
- indexed outcomes
- platform metadata
- agent audit data
- action recommendations
- methods for creating, starting, ending, selecting, and refreshing

Important methods:

- `refreshMeetings()`: calls `listMeetings()`.
- `selectMeeting(id)`: calls `getMeeting(id)` and applies it.
- `createMeetingFromDraft(event)`: posts the draft to the API.
- `startMeetingSession(targetId?)`: starts a meeting.
- `endMeetingSession()`: stops browser capture if needed, ends the meeting, finalizes the report.
- `refreshFinalReport()`: loads or generates final report.

## Why `applyMeeting()` Exists

`applyMeeting(nextMeeting)` centralizes the way the frontend updates meeting state.

It:

- updates the current meeting
- upserts the meeting summary into the list
- updates React Query cache for the meeting

This prevents one API response from updating the detail view while leaving the meeting list stale.

## Status Values

Meeting status is defined as:

```text
draft -> live -> ended
```

Meaning:

- `draft`: meeting exists but capture should not start yet.
- `live`: capture and live state updates are allowed.
- `ended`: report and actions are the main workflow.

## Common Bugs To Watch For

### Starting capture while meeting is still draft

The capture route rejects this with conflict.

Fix:

- call `POST /api/meetings/{meeting_id}/start` first.

### UI showing stale meeting counters

Likely cause:

- `applyMeeting()` or `refreshMeetings()` was not called after a mutation.

Fix:

- after any API mutation that changes a meeting, apply the returned `meeting`.

### Final report not found after ending

Expected if the report has not been generated yet.

Frontend behavior:

- try `GET /final-report`
- if missing, call `POST /final-report`

## Learning Exercise

To understand the lifecycle end to end:

1. Open `apps/web/src/features/meeting-session/context/meeting-session-provider.tsx`.
2. Find `createMeetingFromDraft`.
3. Follow it to `apps/web/src/lib/api.ts`.
4. Follow the route to `services/api/src/visualsprint_api/routes/meetings.py`.
5. Follow the repository method in `repository.py`.
6. Watch how the returned `MeetingDetail` moves back to the UI through `applyMeeting`.
