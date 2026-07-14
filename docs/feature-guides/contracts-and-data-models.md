# Contracts And Data Models

This guide explains the shared data model layer that keeps VisualSprint's frontend, API, and agents aligned.

## Feature Purpose

Contracts are the product language.

They define what a meeting is, what a capture chunk is, what a decision looks like, how evidence is represented, what an agent must return, and how the final report is shaped.

If contracts drift, the system becomes hard to debug because the frontend, API, and agents will disagree about the same business object.

## Main Files

TypeScript contracts:

- `packages/contracts/src/domain.ts`
- `packages/contracts/src/index.ts`

API Pydantic models:

- `services/api/src/visualsprint_api/models.py`

Agents Pydantic models:

- `services/agents/src/visualsprint_agents/models.py`

Frontend usage:

- `apps/web/src/lib/api.ts`
- feature components under `apps/web/src/features/*`
- domain components under `apps/web/src/components/domain/*`

## Why There Are TypeScript And Python Models

The frontend uses TypeScript.

The backend and agents services use Python with Pydantic.

The same product concepts therefore appear in two places:

- TypeScript interfaces for browser code
- Pydantic models for FastAPI request/response validation

This is normal in this repo, but it creates a responsibility:

- when a contract changes, update both sides
- tests should catch obvious mismatch
- docs should refer to the shared product concept, not one language only

## Most Important Product Types

### `MeetingDetail`

Full meeting state for the UI.

Contains:

- lifecycle status
- active capture session
- recent chunks
- latest events
- transcript segments
- screen events
- decisions
- commitments
- blockers
- memory matches
- open questions
- final report
- action recommendations

### `CaptureSessionSummary`

Represents a browser capture session.

Important fields:

- session ID
- status
- track information
- started/ended timestamps
- chunk counts

### `CaptureChunkSummary`

Represents one recorded chunk.

Important fields:

- chunk ID
- `clientChunkId`
- sequence
- lifecycle status
- upload status
- processing status
- MIME type
- duration
- storage object path
- upload target

### `TranscriptSegment`

Represents a piece of spoken content.

Important fields:

- speaker label
- text
- start/end timing
- confidence
- source mode

### `ScreenEvent`

Represents interpreted screen context.

Important fields:

- kind
- title
- detail
- timestamp
- frame timestamp
- source mode

### `EvidenceReference`

Connects an output to source evidence.

Important fields:

- type
- reference ID
- note
- timestamp

Why it matters:

- decisions and blockers should be evidence-backed
- report trust depends on preserving references

## Reasoning Output Types

### `DecisionRecord`

Represents a durable decision.

Common fields:

- summary
- detail
- status
- speaker label
- evidence

### `CommitmentRecord`

Represents a follow-up commitment.

Common fields:

- summary
- owner label
- due hint
- status
- evidence

### `BlockerRecord`

Represents a risk or blocker.

Common fields:

- summary
- severity
- status
- evidence

### `OpenQuestionRecord`

Represents an unresolved question.

Common fields:

- question
- status
- speaker label
- evidence

### `MemoryMatch`

Represents a historical match.

Common fields:

- source meeting ID
- source meeting title
- relation
- strength
- score
- snippet

## Agent Input And Output Contracts

### `ChunkInsight`

This is the API-side chunk reasoning input.

It is assembled from:

- meeting state
- chunk context
- transcript segments
- screen events
- focus areas
- memory matches

### `RegisterAgentOutputsRequest`

This is the API-side output registration shape.

The reasoning agent should produce compatible structured outputs:

- decisions
- commitments
- blockers
- open questions
- memory matches
- resolved record IDs

### `MeetingSummaryPacket`

This is the API-side summary input.

It contains:

- durable records
- highlights
- draft executive summary
- memory highlights

### `FinalReport`

This is the stored final report.

It contains:

- executive summary
- decisions
- commitments
- blockers
- open questions
- memory highlights

## Agents Service Model Names

The agents service uses similar but service-specific model names:

- `ChunkInsightRequest`
- `ReasoningRunResponse`
- `SummaryPacketRequest`
- `FinalReportDraft`
- `ActionAgentRequest`
- `ActionAgentResponse`

These are not random names. They represent the agents service boundary.

The API may use richer product objects, while the agents service uses focused input/output shapes for runtime calls.

## Naming Style

TypeScript uses camelCase:

```text
meetingId
clientChunkId
recordType
ownerLabel
```

Elastic uses snake_case:

```text
meeting_id
record_type
owner_label
```

Python Pydantic models mostly preserve API field names so JSON stays compatible with the frontend.

## Contract Alignment Checklist

When adding or changing a feature, check:

1. `packages/contracts/src/domain.ts`
2. `services/api/src/visualsprint_api/models.py`
3. `services/agents/src/visualsprint_agents/models.py`
4. `apps/web/src/lib/api.ts`
5. tests under `services/api/tests` and `services/agents/tests`

## Common Bugs To Watch For

### Frontend compiles but API rejects payload

Likely cause:

- TypeScript contract changed but Pydantic model did not.

### Agent returns JSON but API ignores fields

Likely cause:

- agent output model and API registration model do not align.

### Elastic search result misses fields

Likely cause:

- mapper dropped a field when converting from product model to Elastic model.

### Evidence disappears in the report

Likely cause:

- output registration or indexed document mapping did not preserve evidence references.

## Learning Exercise

Trace a field called `ownerLabel`:

1. Find it in `packages/contracts/src/domain.ts`.
2. Find it in `services/api/src/visualsprint_api/models.py`.
3. Find it in `services/agents/src/visualsprint_agents/models.py`.
4. Find where the frontend renders it in record cards.
5. Find where Elastic mapping converts it to `owner_label`.
