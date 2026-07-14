# Testing And Debugging

This guide explains how to verify VisualSprint and where to look when something breaks.

## Feature Purpose

Testing is how you know whether the agent-built parts still match the real product behavior.

VisualSprint has several moving pieces:

- frontend UI
- shared contracts
- API control plane
- agents adapter
- ingest service
- media service
- Elastic integration
- Slack/Jira action execution
- Cloud Run deployment

A bug can appear in one layer while the symptom shows up somewhere else.

## Main Test Commands

Run all verification:

```powershell
npm run verify
```

Run frontend checks:

```powershell
npm run lint:web
npm run typecheck:web
```

Run contracts check:

```powershell
npm run check:contracts
```

Run Python service tests:

```powershell
npm run test:services
```

Run agent eval smoke:

```powershell
npm run eval:agents
```

Run targeted API tests:

```powershell
pytest services/api/tests/test_api.py -q
pytest services/api/tests/test_elastic_integration.py -q
```

Run targeted agent tests:

```powershell
pytest services/agents/tests -q
pytest services/agents/tests/test_action_agent.py -q
```

## What Each Test Area Covers

### Web lint and typecheck

Checks:

- React/Next code quality
- TypeScript correctness
- contract usage from frontend
- import errors
- invalid component code

Does not check:

- live backend behavior
- Cloud Run configuration
- real browser capture permission flow

### Contracts check

Checks:

- TypeScript shared package compiles

Useful when:

- adding fields to product types
- changing action/agent/capture models

### API tests

Checks:

- meeting lifecycle
- capture lifecycle
- chunk processing
- output registration
- final report generation
- Elastic mapping/write-back/search fallback
- action approval/execution behavior

### Agents tests

Checks:

- reasoning fallback behavior
- summary fallback behavior
- action recommendation behavior
- engine wrapper normalization
- persistence tool behavior
- agent service API behavior

### Agent eval smoke

Checks:

- fixture-backed reasoning and summary behavior
- high-level agent output expectations

Useful because:

- agents can become too generic
- eval fixtures catch obvious behavior drift

## Debugging By Symptom

### UI cannot load meetings

Check:

1. `NEXT_PUBLIC_VISUALSPRINT_API_BASE_URL`
2. browser console
3. `GET /api/health`
4. `GET /api/meetings`
5. CORS config

Likely files:

- `apps/web/src/lib/api.ts`
- `services/api/src/visualsprint_api/routes/meetings.py`
- `services/api/src/visualsprint_api/config.py`

### Meeting starts but capture cannot start

Check:

1. meeting status is `live`
2. source connector is `browser_live_capture`
3. browser capture support
4. active capture session status

Likely files:

- `use-browser-capture.ts`
- `routes/capture.py`
- `repository.py`

### Live dashboard does not update

Check:

1. `GET /api/meetings/{meeting_id}/events`
2. browser EventSource connection
3. repository revision changes
4. `applyMeeting()` in frontend provider

Likely files:

- `use-meeting-stream.ts`
- `routes/meetings.py`
- `meeting-session-provider.tsx`

### Agent output is missing

Check:

1. `VISUALSPRINT_AGENTS_SERVICE_URL`
2. API `service_clients.py`
3. agents service health
4. agents invocation audit
5. fallback behavior

Useful endpoints:

```text
GET /api/meta/agents/invocations
GET /api/audit/invocations
POST /api/meetings/{meeting_id}/agents/smoke
```

### Search does not return old records

Check:

1. did outputs register?
2. were indexed outcome documents created?
3. is Elastic configured?
4. did write-back run?
5. is the query too narrow?

Useful endpoints:

```text
GET /api/meetings/{meeting_id}/memory/index-documents
GET /api/knowledge/search?q=...
POST /api/meetings/{meeting_id}/memory/search-prior-outcomes
```

### Slack or Jira does not execute

Check:

1. recommendation exists
2. recommendation is approved
3. Slack/Jira secrets are configured
4. executor returned stub or real result

Likely files:

- `routes/actions.py`
- `jira_client.py`
- `slack_client.py`
- `actions-page.tsx`

## Live Smoke Test Flow

Use this when the deployed system is running.

```powershell
$API_URL = "https://your-api-service-url"

Invoke-RestMethod -Method GET -Uri "$API_URL/api/health"
Invoke-RestMethod -Method GET -Uri "$API_URL/api/meta"
```

Create meeting:

```powershell
$body = @{
  title = "VisualSprint Smoke Test"
  participantCount = 3
  sourceConnector = "browser_live_capture"
} | ConvertTo-Json

$meetingResponse = Invoke-RestMethod `
  -Method POST `
  -Uri "$API_URL/api/meetings" `
  -ContentType "application/json" `
  -Body $body

$MEETING_ID = $meetingResponse.meeting.id
```

Run agent smoke:

```powershell
Invoke-RestMethod `
  -Method POST `
  -Uri "$API_URL/api/meetings/$MEETING_ID/agents/smoke" `
  -ContentType "application/json" `
  -Body "{}"
```

Search knowledge:

```powershell
Invoke-RestMethod `
  -Method GET `
  -Uri "$API_URL/api/knowledge/search?q=blocker&limit=5"
```

## How To Keep Commits Clean

Before committing:

```powershell
git status --short
git diff --stat
```

Stage only intended files:

```powershell
git add docs/feature-guides docs/README.md
```

Do not use `git add .` when the worktree has unrelated generated or backend files.

## Learning Exercise

Pick one failing behavior and trace it through layers:

1. frontend API call in `apps/web/src/lib/api.ts`
2. FastAPI route in `services/api/src/visualsprint_api/routes`
3. repository method in `repository.py`
4. service client or downstream service if used
5. Pydantic model validation
6. test file covering the behavior
