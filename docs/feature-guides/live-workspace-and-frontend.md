# Live Workspace And Frontend State

This guide explains how the VisualSprint frontend is organized, how meeting state is shared, and how live updates reach the UI.

## Feature Purpose

The frontend has three main jobs:

1. Let users create and operate a meeting.
2. Show live evidence, reasoning outputs, and capture state.
3. Let users review final reports, actions, and historical knowledge.

The frontend should not own core business logic. It should call the API, render returned state, and handle browser-only capture APIs.

## Route Map

Important Next.js routes:

- `/`: landing page.
- `/meetings`: meeting list.
- `/meetings/new`: setup flow.
- `/meetings/[id]`: status-aware workspace route.
- `/meetings/[id]/live`: live meeting dashboard.
- `/meetings/[id]/report`: final report.
- `/meetings/[id]/actions`: action approval portal.
- `/search`: cross-meeting knowledge search.
- `/dev`: platform and debugging panels.

Important files:

- `apps/web/src/app/*`
- `apps/web/src/features/workspace/meeting-workspace.tsx`
- `apps/web/src/components/layout/app-shell.tsx`
- `apps/web/src/components/layout/meeting-sub-nav.tsx`
- `apps/web/src/components/layout/meeting-top-bar.tsx`

## Workspace View Selection

`MeetingWorkspace` dynamically loads feature pages.

File:

- `apps/web/src/features/workspace/meeting-workspace.tsx`

Why dynamic imports are used:

- keeps route bundles lighter
- avoids loading every feature page immediately
- helps client-only meeting state pages stay isolated

Conceptual behavior:

```text
workspace view
  -> setup page
  -> live page
  -> report page
  -> actions page
  -> dev panels
```

## Central State Provider

File:

- `apps/web/src/features/meeting-session/context/meeting-session-provider.tsx`

This is the most important frontend state file.

It wraps feature pages and exposes:

- current meeting
- meeting list
- draft form state
- loading and error state
- capture state
- stream state
- report state
- chunk insight
- summary packet
- indexed outcomes
- platform metadata
- agent audit data
- action recommendations
- all major mutation methods

## Why The Provider Is Useful

Without the provider, each page would need to separately know how to:

- load meetings
- select a meeting
- start/end meetings
- start/stop capture
- refresh reports
- run agent smoke checks
- generate action recommendations
- approve/reject/execute actions

The provider keeps that workflow in one place.

## Important Provider Methods

### `refreshMeetings()`

Calls:

- `listMeetings()` from `apps/web/src/lib/api.ts`

Purpose:

- keeps the meeting list fresh
- used after create/start/end/demo actions

### `selectMeeting(id)`

Calls:

- `getMeeting(id)`

Purpose:

- loads a full `MeetingDetail`
- updates current workspace state

### `applyMeeting(nextMeeting)`

Purpose:

- updates current meeting state
- updates meeting list summary
- updates React Query cache

Why it matters:

- many API mutations return the updated meeting
- this method prevents stale UI state

### `createMeetingFromDraft()`

Calls:

- `createMeeting(draft)`

Purpose:

- creates a backend meeting from form state
- applies returned meeting
- refreshes list
- shows toast

### `startMeetingSession()`

Calls:

- `startMeeting(meetingId)`

Purpose:

- transitions draft meeting to live

### `endMeetingSession()`

Calls:

- `stopBrowserCapture()` if currently recording
- `endMeeting(meeting.id)`
- `finalizeReport(meeting.id)`

Purpose:

- closes live work
- generates or stores final report

### `runAgentSmokeCheck()`

Calls:

- `runAgentSmoke(meeting.id, latestProcessedChunk?.clientChunkId)`
- `getAgentInvocationAudit()`

Purpose:

- verifies the API-to-agents seam
- useful during cloud setup

### `generateRecommendations()`

Calls:

- `generateActionRecommendations(meeting.id)`

Purpose:

- asks the action agent for Jira/Slack/escalation suggestions

## API Client

File:

- `apps/web/src/lib/api.ts`

This file contains typed wrappers around backend endpoints.

Important features:

- `requestJson()` centralizes JSON fetch behavior.
- GET requests can retry transient failures.
- mutation calls use explicit methods.
- all API paths stay in one place.

Important methods:

- `listMeetings()`
- `createMeeting(payload)`
- `startMeeting(meetingId)`
- `endMeeting(meetingId)`
- `startCaptureSession(meetingId, payload)`
- `registerCaptureChunk(meetingId, payload)`
- `completeCaptureChunkUpload(meetingId, payload)`
- `runCaptureChunkReasoning(meetingId, clientChunkId)`
- `finalizeReport(meetingId)`
- `generateActionRecommendations(meetingId)`
- `approveActionRecommendation(...)`
- `rejectActionRecommendation(...)`
- `executeActionRecommendation(...)`
- `searchKnowledge(params)`

## Live Updates

File:

- `apps/web/src/hooks/use-meeting-stream.ts`

Backend route:

- `GET /api/meetings/{meeting_id}/events`

Transport:

- Server-Sent Events

Why SSE is used:

- the server can push meeting updates
- browser support is simple
- it is lighter than a full WebSocket for this use case

Flow:

1. UI subscribes with `EventSource`.
2. API streams `meeting.updated` events.
3. Hook parses event payload.
4. Hook calls `applyMeeting`.
5. Dashboard re-renders with latest state.

## Live Dashboard Components

Important files:

- `apps/web/src/features/live/live-session-page.tsx`
- `apps/web/src/features/live/components/live-metrics-row.tsx`
- `apps/web/src/features/live/components/capture-panel.tsx`
- `apps/web/src/features/live/components/capture-guide.tsx`
- `apps/web/src/features/live/components/reasoning-panels.tsx`
- `apps/web/src/features/live/components/records-panels.tsx`
- `apps/web/src/features/live/components/memory-panel.tsx`
- `apps/web/src/features/live/components/linked-evidence-feed.tsx`

What each does:

- `LiveSessionPage`: page-level layout.
- `LiveMetricsRow`: count tiles for chunks, transcripts, decisions, blockers, etc.
- `CapturePanel`: current capture status.
- `CaptureGuide`: operational capture controls.
- `ReasoningPanels`: current chunk insight and summary packet.
- `RecordsPanels`: decisions, commitments, blockers, questions.
- `MemoryPanel`: memory matches.
- `LinkedEvidenceFeed`: connects transcript and screen evidence.

## Evidence Linking

File:

- `apps/web/src/lib/evidence-linking.ts`

Purpose:

- connects transcript segments and screen events by time window.

Important methods:

- `toEpochMs(value)`: normalizes timestamps.
- `transcriptMatchesScreenEvent(...)`: checks if transcript and screen event are near each other.
- `findLinkedScreenEvents(...)`: returns screen events near a transcript segment.
- `findLinkedTranscriptSegments(...)`: returns transcript segments near a screen event.
- `resolveEvidenceTargets(...)`: maps evidence references to actual UI records.

Why it matters:

- VisualSprint should not show agent outputs without evidence.
- Linked evidence helps users trust decisions and blockers.

## UI Components

Domain components:

- `DecisionCard`
- `CommitmentCard`
- `BlockerCard`
- `MemoryMatchCard`
- `OpenQuestionCard`
- `TranscriptCard`
- `ScreenEventCard`
- `CaptureChunkCard`
- `CaptureSessionSummary`

Shared UI:

- `Button`
- `Card`
- `EmptyState`
- `Field`
- `Metric`
- `StatusPill`
- `Tabs`
- `ThemeSwitcher`

## Theme System

Main file:

- `apps/web/src/app/globals.css`

The app uses CSS variables for:

- backgrounds
- surfaces
- borders
- foreground text
- brand colors
- accent colors
- status colors

The theme provider switches between supported themes and the UI reads variables rather than hardcoding colors everywhere.

## Common Bugs To Watch For

### Page does not update after backend mutation

Likely cause:

- mutation response was not passed through `applyMeeting()`

### SSE does not connect

Likely causes:

- wrong API base URL
- CORS mismatch
- meeting ID missing
- backend route not deployed

### Capture controls visible but disabled

Likely causes:

- browser capture unsupported
- meeting is not live
- another capture session is active

### Report page empty

Likely causes:

- meeting has not ended
- final report not generated
- API returned 404 and finalize fallback failed

## Learning Exercise

Trace a live dashboard update:

1. Open `use-meeting-stream.ts`.
2. Find the `EventSource` setup.
3. Open `routes/meetings.py`.
4. Find `stream_meeting_events`.
5. Search for repository revision updates in `repository.py`.
6. Watch how an updated `MeetingDetail` reaches `LiveSessionPage`.
