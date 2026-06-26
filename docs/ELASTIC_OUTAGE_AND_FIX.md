# Elastic Outage — Issue Log & Fix Playbook

Last updated: 2026-06-26

## Status

**Elastic is DOWN.** The cluster DNS no longer resolves. All Elastic-backed features degrade gracefully to empty/unavailable states; no crashes or data loss.

---

## What broke

### Symptom

Both Elastic-backed features return empty results:

| Feature | Endpoint | Symptom |
|---|---|---|
| Cross-meeting knowledge search | `GET /api/knowledge/search` | `available: false`, `total: 0` |
| Memory highlights in meeting report | Internal `search_prior_outcomes` call | Returns 0 memory matches |

### Root cause

The Elastic Cloud cluster hostname **no longer resolves in DNS**:

```
Host:    my-elasticsearch-project-ad6723.es.us-central1.gcp.elastic.cloud
Error:   Non-existent domain (NXDOMAIN)
```

The cluster was on an Elastic Cloud **trial** that expired. When a trial expires, Elastic deletes the deployment and removes the DNS record. The cluster had **81 indexed outcome documents** before it went offline.

The GCP secrets `ELASTICSEARCH_URL` and `ELASTICSEARCH_API_KEY` still exist in Secret Manager and still point to the deleted cluster — they are now stale.

### What is NOT broken

Everything else in the stack is fully operational:

- `visualsprint-api` Cloud Run service (us-west1)
- `visualsprint-agents` Cloud Run service (us-west1)
- `visualsprint-web` Cloud Run service (us-west1)
- All three Vertex AI Reasoning Engines (reasoning / summary / action)
- Gemini vision pipeline
- Jira integration (project SCRUM)
- Slack integration (#general-visualsprint-agent)

---

## Code is complete — no code changes needed to restore

The full cross-meeting search stack was implemented and deployed:

**Backend** (`services/api`):
- `elastic_client.py` — `search_outcomes_in_elasticsearch()` with fuzzy multi-match, recency sort, and an unsorted fallback
- `routes/knowledge.py` — `GET /api/knowledge/search?q=&recordType=&limit=`
- `repository.py` — `search_outcomes()` returns `(available=False, [])` when Elastic is unreachable
- `models.py` — `OutcomeSearchResult` and `OutcomeSearchResponse` types

**Frontend** (`apps/web`):
- `src/features/knowledge/knowledge-search-page.tsx` — debounced search box, filter chips (All / Decisions / Commitments / Blockers / Questions), result cards
- `src/app/search/page.tsx` — Next.js route at `/search`
- Sidebar nav includes "Search knowledge" link

The UI shows a graceful "Search isn't available" state when `available: false` — no user-visible crash.

---

## Fix steps

### Step 1 — Restore the Elastic Cloud cluster

Option A — **Restore existing project** (if Elastic support can recover it):
- Log in to https://cloud.elastic.co
- Check if `my-elasticsearch-project-ad6723` appears as suspended/deleted
- Contact Elastic support to restore the deployment and its data

Option B — **Create a new Elastic Cloud project** (fastest path):
1. Go to https://cloud.elastic.co → Create deployment
2. Choose **Elasticsearch Serverless** (or a standard deployment, either works)
3. Region: `us-central1` (GCP) to stay co-located with Cloud Run services
4. After creation, note:
   - Elasticsearch endpoint URL (e.g. `https://my-new-project-abc123.es.us-central1.gcp.elastic.cloud`)
   - Create an API key under Security → API Keys

### Step 2 — Re-create the index

The index name the code expects is stored in the `ELASTIC_INDEX_OUTCOMES` secret (default: `visualsprint_outcomes`).

Create the index with the correct mappings:

```json
PUT /visualsprint_outcomes
{
  "mappings": {
    "properties": {
      "tenant_id":     { "type": "keyword" },
      "meeting_id":    { "type": "keyword" },
      "record_type":   { "type": "keyword" },
      "summary":       { "type": "text" },
      "detail":        { "type": "text" },
      "status":        { "type": "keyword" },
      "owner_label":   { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
      "speaker_label": { "type": "keyword" },
      "due_hint":      { "type": "text" },
      "severity":      { "type": "keyword" },
      "meeting_title": { "type": "text" },
      "updated_at":    { "type": "date" },
      "created_at":    { "type": "date" }
    }
  }
}
```

> **Note:** `updated_at` must be mapped as `date`. If it is mapped as `text`, the sort in `search_outcomes_in_elasticsearch()` will fail — the code has a fallback for this, but proper date mapping gives correct recency ordering.

### Step 3 — Update GCP secrets

Replace the stale URL and API key in Secret Manager:

```bash
# Update the URL
echo -n "https://<new-endpoint>.es.us-central1.gcp.elastic.cloud" | \
  gcloud secrets versions add ELASTICSEARCH_URL \
    --project visualsprint-agent \
    --data-file=-

# Update the API key
echo -n "<new-api-key>" | \
  gcloud secrets versions add ELASTICSEARCH_API_KEY \
    --project visualsprint-agent \
    --data-file=-
```

### Step 4 — Redeploy `visualsprint-api`

```bash
gcloud run deploy visualsprint-api \
  --source services/api \
  --project visualsprint-agent \
  --region us-west1 \
  --allow-unauthenticated
```

The deploy will pick up the new secret versions automatically (secrets are mounted as env vars at startup).

### Step 5 — Verify

```bash
# Health check
curl https://<visualsprint-api-url>/api/health

# Search check (should return available: true)
curl "https://<visualsprint-api-url>/api/knowledge/search?q=blocker&limit=5"
```

Expected response once the cluster is up and at least one meeting has been completed:

```json
{
  "query": "blocker",
  "recordType": null,
  "available": true,
  "total": <n>,
  "results": [...]
}
```

### Step 6 — Re-index historical data (optional)

If Option B (new cluster) was used, the previous 81 documents are lost. They will be re-indexed automatically as new meetings are completed — no manual intervention needed. Historical data from before the outage cannot be recovered unless Elastic support restores the original deployment.

---

## Affected GCP secrets (stale, need updating)

| Secret name | Project | Current state |
|---|---|---|
| `ELASTICSEARCH_URL` | `visualsprint-agent` | Points to deleted cluster — stale |
| `ELASTICSEARCH_API_KEY` | `visualsprint-agent` | Key for deleted cluster — stale |

Secrets that are **not** affected:

| Secret name | Status |
|---|---|
| `GEMINI_API_KEY` | OK |
| `JIRA_API_TOKEN` | OK |
| `JIRA_USER_EMAIL` | OK |
| `SLACK_BOT_TOKEN` | OK |
| `REASONING_ENGINE_ID` | OK |
| `SUMMARY_ENGINE_ID` | OK |
| `ACTION_ENGINE_ID` | OK |

---

## Timeline

| Time | Event |
|---|---|
| Earlier today | Elastic cluster responding normally; 81 documents indexed |
| ~2026-06-26 | DNS for `my-elasticsearch-project-ad6723.es.us-central1.gcp.elastic.cloud` → NXDOMAIN |
| 2026-06-26 | Root cause confirmed: trial cluster expired and was deleted by Elastic |
| 2026-06-26 | All other integrations verified working (Gemini, Vertex, Jira, Slack) |
