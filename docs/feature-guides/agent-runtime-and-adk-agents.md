# Agent Runtime And ADK Agents

This guide explains how VisualSprint uses the agents service, local fallbacks, ADK blueprints, Vertex AI Agent Engine wrappers, and invocation audit.

## Feature Purpose

Agents turn assembled meeting context into structured reasoning outputs.

VisualSprint has three agent categories:

1. Reasoning agent: analyzes one capture chunk.
2. Summary agent: writes the final meeting report summary.
3. Action agent: recommends Jira, Slack, escalation, or manual-review actions.

The agents do not own browser capture, meeting lifecycle, database writes, or UI rendering.

## Main Files

Agent service:

- `services/agents/src/visualsprint_agents/main.py`
- `services/agents/src/visualsprint_agents/reasoning.py`
- `services/agents/src/visualsprint_agents/summary.py`
- `services/agents/src/visualsprint_agents/action.py`
- `services/agents/src/visualsprint_agents/agent_runtime.py`
- `services/agents/src/visualsprint_agents/config.py`
- `services/agents/src/visualsprint_agents/invocation_audit.py`
- `services/agents/src/visualsprint_agents/vertex_normalization.py`

ADK files:

- `services/agents/src/visualsprint_agents/adk/reasoning_agent.py`
- `services/agents/src/visualsprint_agents/adk/summary_agent.py`
- `services/agents/src/visualsprint_agents/adk/action_agent.py`
- `services/agents/src/visualsprint_agents/adk/runtime.py`
- `services/agents/src/visualsprint_agents/adk/engine_wrappers.py`
- `services/agents/src/visualsprint_agents/adk/tool_contracts.py`
- `services/agents/src/visualsprint_agents/adk/tools/*`

API adapter calls:

- `services/api/src/visualsprint_api/service_clients.py`
- `services/api/src/visualsprint_api/routes/agents.py`

## Agents Service HTTP Endpoints

### `GET /api/health`

Implemented by:

- `get_health()` in `services/agents/src/visualsprint_agents/main.py`

Purpose:

- reports service mode
- reports runtime backend
- reports configured/missing agent settings
- reports whether deployment is ready

### `GET /api/audit/invocations`

Implemented by:

- `get_invocation_audit()`

Purpose:

- shows recent agent invocations
- separates reasoning, summary, and action runs
- tracks mock, bridge, bridge-fallback, and configured runtime usage

### `POST /api/reasoning/chunks/run`

Implemented by:

- `run_chunk_reasoning()` in `main.py`
- `run_reasoning_agent()` in `reasoning.py`

Input:

- `ChunkInsightRequest`

Output:

- `ReasoningRunResponse`

### `POST /api/summary/meetings/run`

Implemented by:

- `run_meeting_summary()` in `main.py`
- `run_summary_agent()` in `summary.py`

Input:

- `SummaryPacketRequest`

Output:

- `FinalReportDraft`

### `POST /api/action/meetings/run`

Implemented by:

- `run_meeting_action()` in `main.py`
- `run_action_agent()` in `action.py`

Input:

- `ActionAgentRequest`

Output:

- `ActionAgentResponse`

## Reasoning Agent Flow

The API builds a `ChunkInsight`, then calls the agents service through:

- `run_chunk_reasoning()` in `services/api/src/visualsprint_api/service_clients.py`

The agents service handles it through:

- `run_reasoning_agent()` in `services/agents/src/visualsprint_agents/reasoning.py`

High-level behavior:

1. Receive chunk insight payload.
2. If configured cloud runtime is available, call `invoke_reasoning_agent()`.
3. Validate returned `ReasoningRunResponse`.
4. If configured runtime is unavailable or empty, use fallback behavior.
5. Return structured output only.
6. Record invocation audit.

Output categories:

- decisions
- commitments
- blockers
- open questions
- memory matches
- resolved decision IDs
- resolved commitment IDs
- resolved blocker IDs
- resolved open question IDs

## Summary Agent Flow

The API builds a `MeetingSummaryPacket`, then calls:

- `run_summary_agent()` in `service_clients.py`

The agents service handles:

- `run_summary_agent()` in `services/agents/src/visualsprint_agents/summary.py`

High-level behavior:

1. Receive structured summary packet.
2. Try configured summary runtime.
3. Validate `FinalReportDraft`.
4. Reject weak output that just copies the draft summary.
5. Fall back locally if needed.
6. Return a structured final report draft.

Important detail:

- The API owns final `FinalReport` construction. The summary agent mostly writes `executiveSummary` while preserving structured records from the packet.

## Action Agent Flow

The API calls:

- `run_action_agent(report, meeting_title)` in `service_clients.py`

The agents service handles:

- `run_action_agent()` in `services/agents/src/visualsprint_agents/action.py`

High-level behavior:

1. Receive final report context.
2. Try configured action runtime.
3. Validate `ActionAgentResponse`.
4. Deduplicate recommendations.
5. Fall back locally when the configured runtime is unavailable or empty.
6. Return recommendations for approval, not direct execution.

Recommendation categories:

- `suggest_for_jira`
- `suggest_for_slack`
- `suggest_for_escalation`
- `suggest_for_manual_review`

## Runtime Modes

Configuration model:

- `services/agents/src/visualsprint_agents/config.py`

Important env vars:

- `VISUALSPRINT_AGENT_MODE`
- `VISUALSPRINT_DEPLOYMENT_TARGET`
- `VISUALSPRINT_AGENT_RUNTIME_BACKEND`
- `VISUALSPRINT_GOOGLE_CLOUD_PROJECT_ID`
- `VISUALSPRINT_GOOGLE_CLOUD_LOCATION`
- `VISUALSPRINT_REASONING_ENGINE_RESOURCE_NAME`
- `VISUALSPRINT_SUMMARY_ENGINE_RESOURCE_NAME`
- `VISUALSPRINT_ACTION_ENGINE_RESOURCE_NAME`
- `VISUALSPRINT_REASONING_AGENT_ENDPOINT_URL`
- `VISUALSPRINT_SUMMARY_AGENT_ENDPOINT_URL`
- `VISUALSPRINT_ACTION_AGENT_ENDPOINT_URL`

Modes:

- `mock`: use local deterministic outputs.
- `configured_cloud`: expect cloud runtime configuration.
- `bridge`: call configured endpoint URLs.
- `vertex_ai_reasoning_engine`: call Vertex Agent Engine query endpoint.

## `agent_runtime.py`

This file is the bridge between the agents service and configured cloud runtimes.

Important methods:

- `invoke_reasoning_agent(payload)`
- `invoke_summary_agent(payload)`
- `invoke_action_agent(payload)`
- `_post_json(...)`
- `_query_vertex_reasoning_engine(...)`
- `_resolve_google_access_token()`

### `_query_vertex_reasoning_engine(...)`

Purpose:

- calls the Vertex AI Agent Engine query endpoint

Conceptual endpoint:

```text
https://aiplatform.googleapis.com/v1/{resource_name}:query
```

Why it exists:

- ADK agents are deployed as Agent Engine reasoning engines
- the adapter needs a common way to call them

### `extract_vertex_structured_output(...)`

File:

- `services/agents/src/visualsprint_agents/vertex_normalization.py`

Purpose:

- normalizes different Vertex/agent output shapes into a plain JSON object

Why it matters:

- managed agent runtimes can return structured data in different wrappers
- the code needs a reliable way to find the actual model output

## ADK Blueprints

ADK blueprints live under:

- `services/agents/src/visualsprint_agents/adk`

They define:

- display name
- purpose
- behavior rules
- input contract
- output contract
- tools
- output schema

Important functions:

- `build_reasoning_agent_blueprint()`
- `build_summary_agent_blueprint()`
- `build_action_agent_blueprint()`
- `build_reasoning_agent_scaffold()`
- `build_summary_agent_scaffold()`
- `build_action_agent_scaffold()`
- `create_root_agent(scaffold)`

## Agent Engine Wrappers

File:

- `services/agents/src/visualsprint_agents/adk/engine_wrappers.py`

Purpose:

- exposes Agent Engine-compatible classes with `query()` methods
- validates input and output models
- extracts structured output from ADK event streams

Main wrapper classes:

- `VisualSprintReasoningEngine`
- `VisualSprintSummaryEngine`
- `VisualSprintActionEngine`

Important helper methods:

- `register_query_operations()`
- `run_structured_adk_query(...)`
- `_collect_adk_events(...)`
- `_extract_structured_output(...)`
- `_coalesce_and_validate(...)`

Why coalescing exists:

- LLM output can be incomplete
- wrapper code fills safe defaults where possible
- then Pydantic validation enforces the final contract

## Agent Tools

Tool contract file:

- `services/agents/src/visualsprint_agents/adk/tool_contracts.py`

Tools:

- `register_outputs`
- `finalize_report`
- `search_prior_outcomes`
- `create_action_recommendations`

Tool implementation files:

- `adk/tools/persistence.py`
- `adk/tools/memory.py`
- `adk/tools/actions.py`

Important boundary:

- tools can call deterministic services
- the agent should not directly mutate state unless the flow explicitly gives it a persistence tool
- the API still owns final state correctness

## Invocation Audit

File:

- `services/agents/src/visualsprint_agents/invocation_audit.py`

Purpose:

- records each agent call
- helps prove whether cloud runtime or fallback was used

Useful during deployment because a successful UI response might still be mock fallback. Audit tells you which path was actually used.

## Agent Smoke Route

API route:

- `POST /api/meetings/{meeting_id}/agents/smoke`

Implemented by:

- `services/api/src/visualsprint_api/routes/agents.py`

Purpose:

- tests reasoning and summary agent calls through the API seam
- avoids needing a full user flow just to verify agents

## Common Bugs To Watch For

### Agent output validates locally but fails in API

Likely cause:

- TypeScript contract, API Pydantic model, and agents Pydantic model drifted.

Fix:

- compare `packages/contracts/src/domain.ts`
- compare `services/api/src/visualsprint_api/models.py`
- compare `services/agents/src/visualsprint_agents/models.py`

### Health says deployment is not ready

Likely cause:

- missing required env vars for chosen runtime mode
- placeholder values in Cloud Run YAML
- missing Agent Engine resource names

### Agent appears to work but audit shows mock

Likely cause:

- configured runtime failed and fallback was used
- service URL points to a local fallback
- access token or service account permissions are missing

### Summary agent copies draft summary

The code intentionally rejects weak configured summary output if it simply mirrors the draft.

Fix:

- improve summary agent instructions or structured output extraction.

## Learning Exercise

Trace a chunk reasoning call:

1. Start in `services/api/src/visualsprint_api/repository.py`.
2. Find the chunk reasoning method.
3. Follow the call to `service_clients.run_chunk_reasoning()`.
4. Open `services/agents/src/visualsprint_agents/main.py`.
5. Follow `/api/reasoning/chunks/run`.
6. Open `reasoning.py`.
7. Follow configured runtime call into `agent_runtime.py`.
8. Open `adk/reasoning_agent.py` to see the production blueprint.
9. Open `adk/engine_wrappers.py` to see how deployed ADK output is normalized.
