# Deployment And Configuration

This guide explains how VisualSprint is configured and deployed.

## Feature Purpose

Deployment and configuration are product features in this repo because the app depends on several runtime seams:

- web frontend
- API control plane
- agents service
- ingest service
- media service
- Elastic
- Google Agent Engine
- Slack
- Jira

If configuration is wrong, the UI can still load while important runtime paths silently fall back.

## Main Files

Root:

- `.env.example`
- `deploy.sh`
- `package.json`

Cloud Run:

- `infra/cloud-run/visualsprint-api.service.yaml`
- `infra/cloud-run/visualsprint-agents.service.yaml`
- `infra/cloud-run/visualsprint-ingest.service.yaml`
- `infra/cloud-run/visualsprint-media.service.yaml`
- `infra/cloud-run/deploy-visualsprint.ps1`
- `infra/cloud-run/README.md`

Service config:

- `services/api/src/visualsprint_api/config.py`
- `services/agents/src/visualsprint_agents/config.py`
- `services/ingest/src/visualsprint_ingest/config.py`
- `services/media/src/visualsprint_media/config.py`
- `apps/web/src/lib/env.ts`

GitHub Actions:

- `.github/workflows/*`

## Frontend Configuration

File:

- `apps/web/src/lib/env.ts`

Important public env vars:

- `NEXT_PUBLIC_VISUALSPRINT_API_BASE_URL`
- `NEXT_PUBLIC_VISUALSPRINT_ENABLE_DEV_PANELS`

Rule:

- only values safe for the browser should use `NEXT_PUBLIC_*`

Do not put secrets in:

- Next public env vars
- frontend code
- static JSON files
- docs examples with real keys

## API Configuration

File:

- `services/api/src/visualsprint_api/config.py`

Important config groups:

- CORS origins
- downstream service URLs
- Elastic settings
- agent service URL
- Slack settings
- Jira settings
- service request timeout

Common env vars:

- `VISUALSPRINT_ALLOWED_ORIGINS`
- `VISUALSPRINT_AGENTS_SERVICE_URL`
- `VISUALSPRINT_INGEST_SERVICE_URL`
- `VISUALSPRINT_MEDIA_SERVICE_URL`
- `ELASTICSEARCH_URL`
- `ELASTICSEARCH_API_KEY`
- `ELASTICSEARCH_API_KEY_SECRET`
- `ELASTIC_INDEX_OUTCOMES`
- `SLACK_BOT_TOKEN`
- `SLACK_BOT_TOKEN_SECRET`
- `JIRA_BASE_URL`
- `JIRA_EMAIL`
- `JIRA_API_TOKEN`
- `JIRA_API_TOKEN_SECRET`
- `JIRA_PROJECT_KEY`

Important behavior:

- config builder supports multiple env names in some places
- secrets can be direct values locally or Secret Manager references in deployment
- Elastic write-back should require a real resolved API key, not just a secret-name placeholder

## Agents Service Configuration

File:

- `services/agents/src/visualsprint_agents/config.py`

Important env vars:

- `VISUALSPRINT_AGENT_MODE`
- `VISUALSPRINT_DEPLOYMENT_TARGET`
- `VISUALSPRINT_AGENT_RUNTIME_BACKEND`
- `VISUALSPRINT_GOOGLE_CLOUD_PROJECT_ID`
- `VISUALSPRINT_GOOGLE_CLOUD_LOCATION`
- `VISUALSPRINT_AGENT_APPLICATION_ID`
- `VISUALSPRINT_REASONING_ENGINE_RESOURCE_NAME`
- `VISUALSPRINT_SUMMARY_ENGINE_RESOURCE_NAME`
- `VISUALSPRINT_ACTION_ENGINE_RESOURCE_NAME`
- `VISUALSPRINT_REASONING_AGENT_ENDPOINT_URL`
- `VISUALSPRINT_SUMMARY_AGENT_ENDPOINT_URL`
- `VISUALSPRINT_ACTION_AGENT_ENDPOINT_URL`
- `VISUALSPRINT_ELASTIC_MCP_ENDPOINT`
- `VISUALSPRINT_ELASTIC_API_KEY`
- `VISUALSPRINT_SERVICE_ACCOUNT_EMAIL`

Preferred production mode:

```text
VISUALSPRINT_AGENT_MODE=configured_cloud
VISUALSPRINT_DEPLOYMENT_TARGET=cloud_run
VISUALSPRINT_AGENT_RUNTIME_BACKEND=vertex_ai_reasoning_engine
```

## Cloud Run Services

VisualSprint has separate Cloud Run services:

- API service
- agents service
- ingest service
- media service
- web service

Why separate services:

- each service has a clear responsibility
- cloud-agent config stays isolated
- capture/media processing can scale separately later
- local fallbacks can still work when one downstream service is missing

## Health And Meta Endpoints

API:

- `GET /api/health`
- `GET /api/meta`
- `GET /api/meta/agents/invocations`

Agents:

- `GET /api/health`
- `GET /api/audit/invocations`

Use these after deployment.

Important checks:

- API is reachable
- allowed origins are correct
- agents service URL is configured
- Elastic status is correct
- agent mode is not unexpectedly mock
- missing config list is empty for the intended runtime

## Deployment Verification

Recommended local verification:

```powershell
npm run lint:web
npm run typecheck:web
npm run check:contracts
npm run test:services
npm run verify
```

Recommended live verification:

```powershell
$API_URL = "https://your-api-service-url"

Invoke-RestMethod -Method GET -Uri "$API_URL/api/health"
Invoke-RestMethod -Method GET -Uri "$API_URL/api/meta"
Invoke-RestMethod -Method GET -Uri "$API_URL/api/meetings"
```

Create a smoke meeting:

```powershell
$body = @{
  title = "VisualSprint Smoke Test"
  participantCount = 3
  sourceConnector = "browser_live_capture"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method POST `
  -Uri "$API_URL/api/meetings" `
  -ContentType "application/json" `
  -Body $body
```

Run agent smoke:

```powershell
Invoke-RestMethod `
  -Method POST `
  -Uri "$API_URL/api/meetings/<MEETING_ID>/agents/smoke" `
  -ContentType "application/json" `
  -Body "{}"
```

## Secret Hygiene

Rules:

- never commit real API keys
- keep browser-visible config separate from server secrets
- use Secret Manager for Cloud Run secrets
- prefer secret env refs in service YAML
- avoid printing secrets in logs

High-risk values:

- Slack bot token
- Jira API token
- Elastic API key
- Google API access token
- agent bridge bearer token

## Common Deployment Bugs

### CORS errors in browser

Likely cause:

- frontend origin missing from `VISUALSPRINT_ALLOWED_ORIGINS`

Fix:

- update Cloud Run API env var
- redeploy or update service

### Agents health says not deployment ready

Likely cause:

- missing Agent Engine resource names
- wrong runtime backend
- placeholder app IDs
- service account lacks permissions

### UI loads but actions are stubs

Likely cause:

- Slack/Jira secrets are not configured

### Search unavailable

Likely cause:

- Elastic URL, API key, or index is missing

### Local works, Cloud Run fails

Likely causes:

- env var name mismatch
- Secret Manager IAM missing
- CORS origin mismatch
- service URL points to old revision

## Learning Exercise

To learn deployment wiring:

1. Open `infra/cloud-run/visualsprint-api.service.yaml`.
2. Find all env vars.
3. Open `services/api/src/visualsprint_api/config.py`.
4. Match env vars to settings fields.
5. Open `infra/cloud-run/visualsprint-agents.service.yaml`.
6. Match agent env vars to `services/agents/src/visualsprint_agents/config.py`.
7. Call `/api/meta` and compare live status to expected config.
