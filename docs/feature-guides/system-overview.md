# System Overview

This guide explains the top-level VisualSprint architecture and the main code paths that connect the frontend, FastAPI services, agents, Elastic, and deployment.

## Product Goal

VisualSprint is not just a transcript viewer.

The product goal is to turn meeting activity into durable team records:

- decisions
- commitments
- blockers
- open questions
- historical memory matches
- final evidence-backed reports
- approval-based Jira and Slack recommendations

The important product idea is "system of record." A transcript is raw conversation. VisualSprint tries to identify what the team actually decided, who owns follow-up, what is blocked, and whether this problem appeared before.

## Main Services

### `apps/web`

This is the user-facing Next.js app.

It owns:

- landing page
- meeting list
- meeting setup
- browser capture controls
- live meeting dashboard
- final report view
- action approval portal
- knowledge search UI
- dev panels

Important frontend files:

- `apps/web/src/app/*`: Next.js routes.
- `apps/web/src/features/meeting-session/context/meeting-session-provider.tsx`: central client-side meeting state provider.
- `apps/web/src/features/meeting-session/hooks/use-browser-capture.ts`: browser capture and chunk upload orchestration.
- `apps/web/src/lib/api.ts`: typed frontend API client.
- `apps/web/src/lib/capture.ts`: capture helpers such as chunk IDs, keyframe grabbing, MIME selection, and track metadata.

### `services/api`

This is the deterministic backend control plane.

It owns:

- meeting creation, start, end, and state
- capture session lifecycle
- chunk registration and upload completion
- transcript and screen-event assembly
- chunk insight assembly
- agent-output persistence
- Elastic write-back and search fallback
- summary packet assembly
- final report storage
- action recommendation approval and execution

Important backend files:

- `services/api/src/visualsprint_api/main.py`: FastAPI app and router registration.
- `services/api/src/visualsprint_api/repository.py`: in-memory domain store and most business rules.
- `services/api/src/visualsprint_api/models.py`: Pydantic API models.
- `services/api/src/visualsprint_api/service_clients.py`: adapters to ingest, media, and agents services.
- `services/api/src/visualsprint_api/routes/*.py`: HTTP route modules.

### `services/agents`

This is the agent adapter service.

It owns:

- reasoning agent endpoint
- summary agent endpoint
- action agent endpoint
- local deterministic fallbacks
- configured cloud runtime calls
- Vertex AI Reasoning Engine query support
- Elastic MCP client support
- invocation audit
- ADK agent blueprints and wrappers

Important files:

- `services/agents/src/visualsprint_agents/main.py`: FastAPI endpoints for the agents service.
- `services/agents/src/visualsprint_agents/reasoning.py`: chunk reasoning adapter.
- `services/agents/src/visualsprint_agents/summary.py`: meeting summary adapter.
- `services/agents/src/visualsprint_agents/action.py`: action recommendation adapter.
- `services/agents/src/visualsprint_agents/agent_runtime.py`: bridge and Vertex runtime invocation.
- `services/agents/src/visualsprint_agents/elastic_mcp_client.py`: Elastic MCP tool invocation.
- `services/agents/src/visualsprint_agents/adk/*`: ADK blueprints, runtime helpers, and Agent Engine wrappers.

### `packages/contracts`

This package defines the shared TypeScript product contract.

Important models include:

- `MeetingDetail`
- `CaptureSessionSummary`
- `CaptureChunkSummary`
- `ChunkInsight`
- `MeetingSummaryPacket`
- `RegisterAgentOutputsRequest`
- `FinalReport`
- `IndexedOutcomeDocument`
- `OutcomeSearchResult`
- `ActionRecommendation`

When learning the repo, read `packages/contracts/src/domain.ts` together with `services/api/src/visualsprint_api/models.py`.

The TypeScript and Python models should stay aligned.

## Request Flow From User To Report

High-level flow:

1. User creates a meeting in `apps/web`.
2. Frontend calls `POST /api/meetings`.
3. API stores a `MeetingDetail` in the repository.
4. User starts the meeting.
5. Frontend calls `POST /api/meetings/{meeting_id}/start`.
6. User starts browser capture.
7. Frontend calls `POST /api/meetings/{meeting_id}/capture-sessions/start`.
8. Browser capture hook records small chunks.
9. Frontend registers each chunk with `POST /api/meetings/{meeting_id}/capture-sessions/chunk`.
10. Frontend uploads or acknowledges the chunk with `POST /api/meetings/{meeting_id}/capture-sessions/chunk/upload-complete`.
11. API builds transcript and screen events, then assembles chunk insight.
12. API calls the agents service for chunk reasoning when configured.
13. API persists structured outputs and indexes them into Elastic when configured.
14. Live UI receives state updates through Server-Sent Events.
15. User ends the meeting.
16. API builds a summary packet and calls the summary agent when configured.
17. API stores the final report.
18. User can generate action recommendations.
19. API calls the action agent and stores recommendations for approval.
20. Approved actions can be executed through Slack or Jira integrations.

## Why The Repository Pattern Matters

`services/api/src/visualsprint_api/repository.py` is the core deterministic domain layer.

It is called a repository, but it does more than database access. In this codebase it also owns:

- lifecycle validation
- stable ID generation
- meeting metrics
- output registration
- final report assembly
- action recommendation state transitions
- local memory fallback
- Elastic write-back hooks

This is acceptable for the current hackathon-sized app because the repository is the single source of truth for state behavior.

If the product grows, this file should eventually be split into smaller domain services.

## Deterministic Work Versus Agent Work

Deterministic work is code that should behave the same every time:

- create meeting
- validate meeting status
- enforce active capture session rules
- register chunk sequence
- store output records
- index records into Elastic
- approve or reject action recommendation
- execute approved Jira or Slack action

Agent work is probabilistic reasoning:

- decide whether a transcript/screen signal is durable
- classify decisions, commitments, blockers, and questions
- compare current context with historical memory
- write final executive summary
- recommend downstream actions

The code tries to keep this separation clean.

## Why `services/agents` Exists

The API could call Google Agent Engine directly, but this repo keeps a separate agents service for three reasons:

1. It preserves a stable HTTP seam between the control plane and agent runtime.
2. It lets local development use deterministic fallbacks.
3. It keeps cloud-agent configuration isolated from the core API.

That is why `services/api` calls `VISUALSPRINT_AGENTS_SERVICE_URL`, and `services/agents` decides whether to use mock behavior, bridge mode, or Vertex AI Reasoning Engine mode.

## Important Runtime Modes

The agents service supports:

- `mock`: local deterministic fallback.
- `configured_cloud`: cloud-oriented adapter mode.
- `bridge`: calls configured external agent endpoints.
- `vertex_ai_reasoning_engine`: calls Vertex AI Agent Engine query endpoints.

The intended production path is:

1. ADK agent code in `services/agents`.
2. Deploy to Vertex AI Agent Engine.
3. Register in Gemini Enterprise.
4. Configure `services/agents` to call the deployed Agent Engine resources.

## How To Debug The Whole System

Useful checks:

- `GET /api/health`: API process is alive.
- `GET /api/meta`: platform and downstream service status.
- `GET /api/meta/agents/invocations`: agent invocation audit via the API.
- `GET /api/audit/invocations` on the agents service: direct agents audit.
- `GET /api/meetings`: current meeting list.
- `GET /api/meetings/{meeting_id}/state`: current meeting state snapshot.
- `GET /api/meetings/{meeting_id}/memory/index-documents`: indexed outcome documents for a meeting.
- `GET /api/knowledge/search?q=...`: cross-meeting knowledge search.

Useful local verification:

```powershell
npm run lint:web
npm run typecheck:web
npm run check:contracts
npm run test:services
npm run verify
```

## Mental Model

Think of VisualSprint as a pipeline:

```text
Browser UI
  -> FastAPI control plane
  -> capture chunks
  -> transcript and screen context
  -> chunk insight
  -> reasoning agent
  -> persisted outcomes
  -> Elastic memory
  -> final summary agent
  -> report
  -> action recommendation agent
  -> approval portal
  -> Slack/Jira execution
```

The frontend shows state. The API owns state. The agents produce structured suggestions. Elastic stores memory. Integrations only run after approval.
