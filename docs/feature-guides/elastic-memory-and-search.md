# Elastic Memory And Knowledge Search

This guide explains how VisualSprint stores historical outcomes and searches them later.

## Feature Purpose

Elastic memory lets VisualSprint answer:

- did this blocker appear before?
- did we already decide this?
- who owned a similar commitment last time?
- is this a reopened issue or a new issue?
- can users search past meeting knowledge from the web UI?

There are two related but different features:

1. Agent-time memory retrieval: reasoning agent uses `search_prior_outcomes`.
2. User-facing knowledge search: `/search` page searches indexed outcomes.

## Main Files

API:

- `services/api/src/visualsprint_api/routes/memory.py`
- `services/api/src/visualsprint_api/routes/knowledge.py`
- `services/api/src/visualsprint_api/elastic_client.py`
- `services/api/src/visualsprint_api/elastic_mapping.py`
- `services/api/src/visualsprint_api/elastic_models.py`
- `services/api/src/visualsprint_api/repository.py`
- `services/api/src/visualsprint_api/config.py`

Agents:

- `services/agents/src/visualsprint_agents/elastic_mcp_client.py`
- `services/agents/src/visualsprint_agents/adk/tools/memory.py`
- `services/agents/src/visualsprint_agents/adk/tool_contracts.py`

Frontend:

- `apps/web/src/features/knowledge/knowledge-search-page.tsx`
- `apps/web/src/lib/api.ts`

Contracts:

- `packages/contracts/src/domain.ts`

## Main Models

### `IndexedOutcomeDocument`

This is the repo-native indexed outcome shape.

It includes:

- `id`
- `meetingId`
- `recordType`
- `summary`
- `detail`
- `status`
- `ownerLabel`
- `speakerLabel`
- `dueHint`
- `severity`
- `firstSeenChunkId`
- `lastUpdatedChunkId`
- `createdAt`
- `updatedAt`
- `evidence`

### `ElasticOutcomeDocument`

This is the Elastic-specific document model.

It includes the same core fields plus:

- `tenant_id`
- `meeting_title`

The mapper adds these fields because Elastic search needs cross-meeting and tenant-aware context.

### `MemoryMatch`

This is what the product shows or returns when a historical outcome is relevant.

Important fields:

- `id`
- `sourceMeetingId`
- `sourceMeetingTitle`
- `summary`
- `strength`
- `relation`
- `score`
- `snippet`
- `recordedAt`

## Write-Back Flow

The API owns deterministic Elastic write-back.

Conceptual flow:

1. Agent outputs are registered.
2. Repository updates decisions, commitments, blockers, and questions.
3. Repository builds `IndexedOutcomeDocument` records.
4. API maps those to `ElasticOutcomeDocument`.
5. API upserts them into Elasticsearch if configured.
6. Local in-memory indexed documents remain available for development and diagnostics.

Important seam:

- `POST /api/meetings/{meeting_id}/outputs/register`

Implemented by:

- `routes/outputs.py`
- repository output registration methods
- Elastic write-back helper calls

## Mapping To Elastic

File:

- `services/api/src/visualsprint_api/elastic_mapping.py`

Important methods:

### `map_indexed_outcome_to_elastic_document(...)`

Purpose:

- converts repo-native `IndexedOutcomeDocument` into Elastic-specific `ElasticOutcomeDocument`

Why it exists:

- the product model uses frontend-friendly camelCase fields
- Elastic document fields use search/index-friendly snake_case fields
- tenant and meeting title are added during indexing

### `build_elasticsearch_document_body(document)`

Purpose:

- converts a Pydantic model into the JSON body sent to Elasticsearch

Important behavior:

- converts timestamps to ISO strings
- preserves evidence with `model_dump(mode="json")`

### `map_elastic_document_to_memory_match(...)`

Purpose:

- converts an Elastic hit back into a product `MemoryMatch`

Relation logic:

- `reopened` if document status is reopened
- `resolved_previously` if document status is resolved
- `recurring` if document is not resolved

Strength logic:

- high score means `critical`
- medium score means `recurring`
- lower score means `related`

## Elastic Client

File:

- `services/api/src/visualsprint_api/elastic_client.py`

Important methods:

### `upsert_indexed_outcomes_to_elasticsearch(...)`

Purpose:

- writes changed outcome records into Elastic

Expected behavior:

- use stable document IDs
- upsert records instead of duplicating
- do nothing when Elastic is not configured

### `search_prior_outcomes_in_elasticsearch(...)`

Purpose:

- searches historical outcomes for agent memory retrieval

Used for:

- recurring blockers
- reopened issues
- resolved previous decisions

### `search_outcomes_in_elasticsearch(...)`

Purpose:

- searches indexed outcomes for the user-facing knowledge search page

Used by:

- `GET /api/knowledge/search`

### `_elastic_request_json(...)`

Purpose:

- centralizes HTTP calls to Elastic
- attaches authentication
- parses JSON responses

## Memory Route

Route:

- `POST /api/meetings/{meeting_id}/memory/search-prior-outcomes`

Implemented by:

- `search_prior_outcomes()` in `routes/memory.py`
- `repository.search_prior_outcomes(meeting_id, payload)`

Input:

- `SearchPriorOutcomesRequest`

Purpose:

- searches prior outcomes for a specific candidate signal
- used as local fallback or diagnostic route

Important boundary:

- retrieval returns candidates
- the reasoning agent decides whether relation is new, recurring, reopened, or resolved previously

## Knowledge Search Route

Route:

- `GET /api/knowledge/search`

Implemented by:

- `search_knowledge()` in `routes/knowledge.py`
- `repository.search_outcomes(query, record_type, limit)`

Query params:

- `q`
- `recordType`
- `limit`

Output:

- `OutcomeSearchResponse`

Purpose:

- lets users search decisions, commitments, blockers, and questions across meetings

Frontend:

- `apps/web/src/features/knowledge/knowledge-search-page.tsx`

## Agent MCP Memory Tool

Tool name:

- `search_prior_outcomes`

Files:

- `services/agents/src/visualsprint_agents/adk/tools/memory.py`
- `services/agents/src/visualsprint_agents/elastic_mcp_client.py`

Agent flow:

1. Reasoning agent detects a durable candidate signal.
2. Agent calls `search_prior_outcomes`.
3. Tool calls Elastic MCP when configured.
4. Tool returns ranked candidates.
5. Agent uses current chunk plus historical matches to classify relation.

The tool does not make the final reasoning decision.

## Configuration

API Elastic settings live in:

- `services/api/src/visualsprint_api/config.py`

Common env vars:

- `ELASTICSEARCH_URL`
- `ELASTICSEARCH_API_KEY`
- `ELASTICSEARCH_API_KEY_SECRET`
- `ELASTIC_INDEX_OUTCOMES`
- `ELASTIC_MCP_SERVER_URL`

Agents MCP settings live in:

- `services/agents/src/visualsprint_agents/config.py`

Common env vars:

- `VISUALSPRINT_ELASTIC_MCP_ENDPOINT`
- `VISUALSPRINT_ELASTIC_API_KEY`
- `VISUALSPRINT_ELASTIC_API_KEY_SECRET_NAME`

Security rule:

- do not put real Elastic API keys in frontend code
- do not commit real keys to the repo
- use Secret Manager or runtime-only env vars

## Local Fallback Behavior

VisualSprint keeps local fallback behavior so development still works without Elastic.

Fallback behavior:

- API can keep indexed outcomes in memory
- memory search can use local keyword matching
- knowledge search can return local indexed results
- Elastic-specific routes report availability state

Why this is useful:

- frontend stays usable
- tests stay deterministic
- development does not require cloud credentials

## Common Bugs To Watch For

### Search says unavailable

Likely causes:

- Elastic URL missing
- API key missing
- index name missing
- Elastic write-back disabled or not configured

### Agent marks everything new

Likely causes:

- MCP endpoint missing
- Elastic has no documents
- query text is too weak
- reasoning prompt is not calling `search_prior_outcomes`

### Duplicate records in Elastic

Likely cause:

- unstable IDs are used during indexing

Fix:

- keep stable `IndexedOutcomeDocument.id`
- upsert by ID

### Search results lack evidence

Likely cause:

- mapper dropped evidence references

Fix:

- check `map_indexed_outcome_to_elastic_document`
- check `build_elasticsearch_document_body`

## Learning Exercise

Trace one decision into search:

1. Agent returns a decision in `RegisterAgentOutputsRequest`.
2. API route `outputs.py` calls repository registration.
3. Repository stores or updates the decision.
4. Repository builds an `IndexedOutcomeDocument`.
5. `elastic_mapping.py` maps it to `ElasticOutcomeDocument`.
6. `elastic_client.py` upserts it.
7. `/api/knowledge/search?q=...` searches it.
8. `KnowledgeSearchPage` renders the result.
