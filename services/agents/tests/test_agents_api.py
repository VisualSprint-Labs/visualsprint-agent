from __future__ import annotations

from fastapi.testclient import TestClient

import visualsprint_agents.elastic_mcp_client as elastic_mcp_module
import visualsprint_agents.agent_runtime as agent_runtime_module
import visualsprint_agents.reasoning as reasoning_module
import visualsprint_agents.summary as summary_module
from visualsprint_agents.models import (
    ChunkInsightRequest,
    FinalReportDraft,
    ReasoningRunResponse,
    SummaryPacketRequest,
)
from visualsprint_agents.config import build_settings
from visualsprint_agents.adk import (
    build_reasoning_agent_blueprint,
    build_reasoning_agent_scaffold,
    build_reasoning_root_agent,
    build_summary_agent_blueprint,
    build_summary_agent_scaffold,
    build_summary_root_agent,
)
from visualsprint_agents.adk.tools import (
    finalize_report,
    register_outputs,
    search_prior_outcomes,
)
from visualsprint_agents.evals import (
    load_reasoning_eval_fixtures,
    load_summary_eval_fixtures,
    run_agent_eval_smoke,
)
from visualsprint_agents.main import app
from visualsprint_agents.vertex_normalization import extract_vertex_structured_output


def test_agents_health_reasoning_and_summary():
    with TestClient(app) as client:
        health_response = client.get("/api/health")
        assert health_response.status_code == 200
        health_payload = health_response.json()
        assert health_payload["service"] == "visualsprint-agents"
        assert health_payload["mode"] == "mock"
        assert health_payload["runtimeBackend"] == "bridge"
        assert health_payload["deploymentTarget"] == "local_dev"
        assert health_payload["deploymentReady"] is True
        assert health_payload["reasoningAgentConfigured"] is False
        assert health_payload["summaryAgentConfigured"] is False
        assert health_payload["reasoningEngineResourceConfigured"] is False
        assert health_payload["summaryEngineResourceConfigured"] is False
        assert health_payload["reasoningEndpointConfigured"] is False
        assert health_payload["summaryEndpointConfigured"] is False
        assert health_payload["bridgeAuthConfigured"] is False
        assert health_payload["googleAccessTokenConfigured"] is False
        assert health_payload["secretManagerConfigured"] is False
        assert health_payload["cloudRunServiceConfigured"] is False
        assert health_payload["elasticMcpConfigured"] is False
        assert health_payload["allowedOriginsConfigured"] == 0
        assert health_payload["missingConfiguration"] == []

        reasoning_response = client.post(
            "/api/reasoning/chunks/run",
            json={
                "meetingId": "mtg_agents_001",
                "meetingTitle": "Planning sync",
                "meetingNotes": "Track delivery risk.",
                "clientChunkId": "client-chunk-agents-001",
                "focusSummary": "Chunk 1 centers on release stability.",
                "attentionFlags": ["Flag"],
                "reasoningChecklist": ["Checklist"],
                "focusAreas": [
                    {
                        "recordType": "decision",
                        "summary": "Release stability",
                        "detail": "The team needs a concrete decision.",
                        "evidence": ["Jordan: We should decide today."],
                    }
                ],
            },
        )
        assert reasoning_response.status_code == 200
        reasoning_payload = reasoning_response.json()
        assert reasoning_payload["clientChunkId"] == "client-chunk-agents-001"
        assert len(reasoning_payload["decisions"]) == 1

        summary_response = client.post(
            "/api/summary/meetings/run",
            json={
                "meetingId": "mtg_agents_001",
                "meetingTitle": "Planning sync",
                "meetingStatus": "ended",
                "draftExecutiveSummary": "This meeting produced durable outcomes.",
                "decisions": [
                    {
                        "title": "Decide on release stability",
                        "rationale": "The team aligned on a concrete direction.",
                        "speakerLabel": "ReasoningAgent",
                        "status": "open",
                    }
                ],
                "commitments": [],
                "blockers": [],
                "openQuestions": [],
                "memoryHighlights": [],
            },
        )
        assert summary_response.status_code == 200
        summary_payload = summary_response.json()
        assert summary_payload["meetingId"] == "mtg_agents_001"
        assert "durable outcomes" in summary_payload["executiveSummary"]

        audit_response = client.get("/api/audit/invocations")
        assert audit_response.status_code == 200
        audit_payload = audit_response.json()
        assert audit_payload["summary"]["total"] == 2
        assert audit_payload["summary"]["mockRuns"] == 2
        assert audit_payload["summary"]["bridgeRuns"] == 0
        assert audit_payload["summary"]["bridgeFallbackRuns"] == 0
        assert audit_payload["invocations"][0]["agentKind"] == "summary"
        assert audit_payload["invocations"][1]["agentKind"] == "reasoning"


def test_build_settings_supports_configured_cloud_mode():
    settings = build_settings(
        {
            "VISUALSPRINT_ENV": "production",
            "VISUALSPRINT_TRACK": "elastic",
            "VISUALSPRINT_AGENT_MODE": "configured_cloud",
            "VISUALSPRINT_DEPLOYMENT_TARGET": "cloud_run",
            "VISUALSPRINT_GOOGLE_CLOUD_PROJECT_ID": "demo-project",
            "VISUALSPRINT_GOOGLE_CLOUD_LOCATION": "us-central1",
            "VISUALSPRINT_AGENT_APPLICATION_ID": "agents-app",
            "VISUALSPRINT_REASONING_AGENT_ID": "reasoning-agent",
            "VISUALSPRINT_SUMMARY_AGENT_ID": "summary-agent",
            "VISUALSPRINT_ACTION_AGENT_ID": "action-agent",
            "VISUALSPRINT_REASONING_AGENT_ENDPOINT_URL": "https://agents.example/reasoning",
            "VISUALSPRINT_SUMMARY_AGENT_ENDPOINT_URL": "https://agents.example/summary",
            "VISUALSPRINT_ACTION_AGENT_ENDPOINT_URL": "https://agents.example/action",
            "VISUALSPRINT_AGENT_BRIDGE_BEARER_TOKEN_SECRET_NAME": "agents-bridge-token",
            "VISUALSPRINT_ELASTIC_MCP_ENDPOINT": "https://elastic.example/mcp",
            "VISUALSPRINT_ELASTIC_API_KEY": "elastic-api-key-value",
            "VISUALSPRINT_ELASTIC_API_KEY_SECRET_NAME": "elastic-api-key",
            "VISUALSPRINT_SERVICE_ACCOUNT_EMAIL": "svc@demo-project.iam.gserviceaccount.com",
            "VISUALSPRINT_CLOUD_RUN_SERVICE_URL": "https://visualsprint-agents-abc.a.run.app",
            "VISUALSPRINT_ALLOWED_ORIGINS": "https://app.visualsprint.dev, https://staging.visualsprint.dev",
        }
    )

    assert settings.environment == "production"
    assert settings.agent_mode == "configured_cloud"
    assert settings.agent_runtime_backend == "bridge"
    assert settings.deployment_target == "cloud_run"
    assert settings.reasoning_agent_configured is True
    assert settings.summary_agent_configured is True
    assert settings.reasoning_endpoint_configured is True
    assert settings.summary_endpoint_configured is True
    assert settings.bridge_auth_configured is True
    assert settings.secret_manager_configured is True
    assert settings.cloud_run_service_configured is True
    assert settings.elastic_mcp_configured is True
    assert settings.cloud_adapter_ready is True
    assert settings.deployment_ready is True
    assert settings.allowed_origins == (
        "https://app.visualsprint.dev",
        "https://staging.visualsprint.dev",
    )
    assert settings.missing_cloud_configuration == ()


def test_build_settings_reports_missing_cloud_run_requirements():
    settings = build_settings(
        {
            "VISUALSPRINT_AGENT_MODE": "configured_cloud",
            "VISUALSPRINT_DEPLOYMENT_TARGET": "cloud_run",
            "VISUALSPRINT_GOOGLE_CLOUD_PROJECT_ID": "demo-project",
            "VISUALSPRINT_REASONING_AGENT_ID": "reasoning-agent",
        }
    )

    assert settings.deployment_target == "cloud_run"
    assert settings.deployment_ready is False
    assert "VISUALSPRINT_SUMMARY_AGENT_ID" in settings.missing_cloud_configuration
    assert "VISUALSPRINT_REASONING_AGENT_ENDPOINT_URL" in settings.missing_cloud_configuration
    assert "VISUALSPRINT_SUMMARY_AGENT_ENDPOINT_URL" in settings.missing_cloud_configuration


def test_build_settings_supports_vertex_ai_runtime_backend():
    settings = build_settings(
        {
            "VISUALSPRINT_AGENT_MODE": "configured_cloud",
            "VISUALSPRINT_AGENT_RUNTIME_BACKEND": "vertex_ai_reasoning_engine",
            "VISUALSPRINT_GOOGLE_CLOUD_PROJECT_ID": "demo-project",
            "VISUALSPRINT_ACTION_ENGINE_RESOURCE_NAME": "projects/demo-project/locations/us-central1/reasoningEngines/action789",
            "VISUALSPRINT_REASONING_ENGINE_RESOURCE_NAME": "projects/demo-project/locations/us-central1/reasoningEngines/reasoning123",
            "VISUALSPRINT_SUMMARY_ENGINE_RESOURCE_NAME": "projects/demo-project/locations/us-central1/reasoningEngines/summary456",
            "VISUALSPRINT_GOOGLE_API_ACCESS_TOKEN": "ya29.sample-token",
        }
    )

    assert settings.agent_runtime_backend == "vertex_ai_reasoning_engine"
    assert settings.reasoning_engine_resource_configured is True
    assert settings.summary_engine_resource_configured is True
    assert settings.google_access_token_configured is True
    assert settings.cloud_adapter_ready is True
    assert settings.deployment_ready is True


def test_vertex_runtime_prefers_explicit_query_urls(monkeypatch):
    monkeypatch.setattr(
        agent_runtime_module,
        "settings",
        build_settings(
            {
                "VISUALSPRINT_AGENT_MODE": "configured_cloud",
                "VISUALSPRINT_AGENT_RUNTIME_BACKEND": "vertex_ai_reasoning_engine",
                "VISUALSPRINT_GOOGLE_CLOUD_PROJECT_ID": "visualsprint-agent",
                "VISUALSPRINT_REASONING_ENGINE_RESOURCE_NAME": "projects/530780341550/locations/us-west1/reasoningEngines/554162656492126208",
                "VISUALSPRINT_SUMMARY_ENGINE_RESOURCE_NAME": "projects/530780341550/locations/us-west1/reasoningEngines/6620511354560184320",
                "VISUALSPRINT_ACTION_ENGINE_RESOURCE_NAME": "projects/530780341550/locations/us-west1/reasoningEngines/7293799498852073472",
                "VISUALSPRINT_GOOGLE_API_ACCESS_TOKEN": "ya29.sample-token",
                "VISUALSPRINT_REASONING_QUERY_URL": "https://custom.example/reasoning-query",
            }
        ),
    )

    captured: dict[str, str | None] = {}

    def fake_query(*, resource_name, input_payload, query_url=None):
        captured["resource_name"] = resource_name
        captured["query_url"] = query_url
        return {
            "structuredContent": {
                "clientChunkId": input_payload["clientChunkId"],
                "decisions": [],
                "commitments": [],
                "blockers": [],
                "openQuestions": [],
                "memoryMatches": [],
                "resolvedDecisionIds": [],
                "resolvedCommitmentIds": [],
                "resolvedBlockerIds": [],
                "resolvedOpenQuestionIds": [],
            }
        }

    monkeypatch.setattr(agent_runtime_module, "_query_vertex_reasoning_engine", fake_query)
    monkeypatch.setattr(
        agent_runtime_module,
        "extract_vertex_structured_output",
        lambda response: response["structuredContent"],
    )

    result = agent_runtime_module.invoke_reasoning_agent(
        ChunkInsightRequest(
            meetingId="mtg_agent_runtime_001",
            meetingTitle="Planning sync",
            meetingNotes="Track delivery risk.",
            clientChunkId="client-chunk-agent-runtime-001",
            focusSummary="Chunk 1 centers on release stability.",
            attentionFlags=["Flag"],
            reasoningChecklist=["Checklist"],
            focusAreas=[
                {
                    "recordType": "decision",
                    "summary": "Release stability",
                    "detail": "The team needs a concrete decision.",
                    "evidence": ["Jordan: We should decide today."],
                }
            ],
        )
    )

    assert result is not None
    assert captured["resource_name"].endswith("/554162656492126208")
    assert captured["query_url"] == "https://custom.example/reasoning-query"


def test_adk_blueprints_match_repo_contracts():
    reasoning_blueprint = build_reasoning_agent_blueprint()
    summary_blueprint = build_summary_agent_blueprint()

    assert reasoning_blueprint.input_contract == "ChunkInsight"
    assert reasoning_blueprint.output_contract == "ReasoningRunResponse"
    assert len(reasoning_blueprint.tools) == 2
    assert summary_blueprint.input_contract == "MeetingSummaryPacket"
    assert summary_blueprint.output_contract == "FinalReportDraft"
    assert len(summary_blueprint.tools) == 1


def test_adk_scaffolds_export_schema_and_tool_alignment():
    reasoning_scaffold = build_reasoning_agent_scaffold()
    summary_scaffold = build_summary_agent_scaffold()

    assert reasoning_scaffold.input_schema["title"] == "ChunkInsightRequest"
    assert reasoning_scaffold.output_schema["title"] == "ReasoningRunResponse"
    assert [tool.__name__ for tool in reasoning_scaffold.tools] == [
        "search_prior_outcomes",
        "register_outputs",
    ]
    assert reasoning_scaffold.enforce_output_schema is True
    assert summary_scaffold.input_schema["title"] == "SummaryPacketRequest"
    assert summary_scaffold.output_schema["title"] == "FinalReportDraft"
    assert [tool.__name__ for tool in summary_scaffold.tools] == ["finalize_report"]
    assert summary_scaffold.enforce_output_schema is True


def test_adk_root_agents_build_either_real_adk_agents_or_scaffolds():
    reasoning_root = build_reasoning_root_agent()
    summary_root = build_summary_root_agent()

    assert (
        getattr(reasoning_root, "agent_id", None)
        or getattr(reasoning_root, "name", None)
    ) == "visualsprint_reasoning_agent"
    assert (
        getattr(summary_root, "agent_id", None)
        or getattr(summary_root, "name", None)
    ) == "visualsprint_summary_agent"


def test_adk_placeholder_tools_expose_expected_contract_notes():
    search_result = search_prior_outcomes(
        recordType="blocker",
        summary="Release risk",
        detail="A dependency is slipping.",
    )
    register_result = register_outputs(
        meetingId="mtg_adk_001",
        clientChunkId="chunk_adk_001",
        payload={"decisions": [], "blockers": []},
    )
    finalize_result = finalize_report(
        meetingId="mtg_adk_001",
        report={"executiveSummary": "Done"},
    )

    assert search_result["status"] == "not_configured"
    assert search_result["matches"] == []
    assert register_result["status"] == "deferred"
    assert register_result["acceptedKeys"] == ["blockers", "decisions"]
    assert finalize_result["status"] == "deferred"
    assert finalize_result["acceptedKeys"] == ["executiveSummary"]


def test_elastic_mcp_tool_returns_not_configured_without_runtime_endpoint(monkeypatch):
    monkeypatch.setattr(
        elastic_mcp_module,
        "settings",
        build_settings({}),
    )

    result = search_prior_outcomes(
        recordType="blocker",
        summary="Release risk",
        detail="A dependency is slipping.",
    )

    assert result["status"] == "not_configured"
    assert result["matches"] == []


def test_elastic_mcp_tool_can_parse_structured_content_response(monkeypatch):
    monkeypatch.setattr(
        elastic_mcp_module,
        "settings",
        build_settings(
            {
                "VISUALSPRINT_ELASTIC_MCP_ENDPOINT": "https://elastic.example/mcp",
                "VISUALSPRINT_ELASTIC_API_KEY": "elastic-api-key-value",
            }
        ),
    )
    responses = iter(
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "capabilities": {"tools": {"listChanged": True}},
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "elastic-mcp-server", "version": "0.0.1"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 2,
                "result": {
                    "structuredContent": {
                        "matches": [
                            {
                                "sourceMeetingId": "mtg_hist_auth_01",
                                "summary": "A prior auth blocker was found.",
                                "sourceMeetingTitle": "Sprint 21 release review",
                                "strength": "recurring",
                                "relation": "recurring",
                                "score": 0.91,
                                "snippet": "Auth drift blocked the same release path earlier.",
                            }
                        ],
                        "note": "Elastic MCP returned a recurring match.",
                    }
                },
            },
        ]
    )
    monkeypatch.setattr(
        elastic_mcp_module,
        "_mcp_request",
        lambda **kwargs: (next(responses), {}),
    )
    monkeypatch.setattr(
        elastic_mcp_module,
        "_mcp_notify",
        lambda **kwargs: None,
    )

    result = search_prior_outcomes(
        recordType="blocker",
        summary="Auth drift is still blocking release",
        detail="The same release path is affected again.",
        tenantId="default",
        meetingId="mtg_current_001",
    )

    assert result["status"] == "ok"
    assert result["matches"][0]["sourceMeetingId"] == "mtg_hist_auth_01"
    assert result["matches"][0]["relation"] == "recurring"
    assert "Elastic MCP returned" in result["note"]


def test_elastic_mcp_client_threads_session_id_to_tools_call(monkeypatch):
    """The Mcp-Session-Id from initialize must be sent on tools/call."""

    monkeypatch.setattr(
        elastic_mcp_module,
        "settings",
        build_settings(
            {
                "VISUALSPRINT_ELASTIC_MCP_ENDPOINT": "https://elastic.example/mcp",
                "VISUALSPRINT_ELASTIC_API_KEY": "elastic-api-key-value",
            }
        ),
    )

    captured_calls: list[dict] = []

    init_body = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "capabilities": {},
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "elastic-mcp", "version": "0.0.1"},
        },
    }
    init_headers = {"Mcp-Session-Id": "test-session-abc-123"}

    tool_body = {
        "jsonrpc": "2.0",
        "id": 2,
        "result": {
            "structuredContent": {
                "matches": [],
                "note": "No matches found.",
            }
        },
    }
    responses = iter([(init_body, init_headers), (tool_body, {})])

    def fake_mcp_request(**kwargs):
        captured_calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(elastic_mcp_module, "_mcp_request", fake_mcp_request)
    monkeypatch.setattr(elastic_mcp_module, "_mcp_notify", lambda **kwargs: None)

    result = search_prior_outcomes(
        recordType="blocker",
        summary="Auth drift",
        detail="Release path blocked",
    )

    assert result["status"] == "ok"
    assert len(captured_calls) == 2
    assert captured_calls[0]["method"] == "initialize"
    assert captured_calls[1]["method"] == "tools/call"
    assert captured_calls[1].get("extra_headers") == {
        "Mcp-Session-Id": "test-session-abc-123"
    }


def test_vertex_normalization_handles_multiple_response_shapes():
    direct = extract_vertex_structured_output(
        {"output": {"clientChunkId": "chunk-1", "decisions": []}}
    )
    assert direct == {"clientChunkId": "chunk-1", "decisions": []}

    stringified = extract_vertex_structured_output(
        {"output": "{\"clientChunkId\":\"chunk-2\",\"decisions\":[]}"}
    )
    assert stringified == {"clientChunkId": "chunk-2", "decisions": []}

    content_parts = extract_vertex_structured_output(
        {
            "response": {
                "output": {
                    "content": {
                        "parts": [
                            {
                                "text": "{\"clientChunkId\":\"chunk-3\",\"decisions\":[]}"
                            }
                        ]
                    }
                }
            }
        }
    )
    assert content_parts == {"clientChunkId": "chunk-3", "decisions": []}


def test_vertex_ai_runtime_mode_records_vertex_ai_audit(monkeypatch):
    vertex_settings = build_settings(
        {
            "VISUALSPRINT_AGENT_MODE": "configured_cloud",
            "VISUALSPRINT_AGENT_RUNTIME_BACKEND": "vertex_ai_reasoning_engine",
            "VISUALSPRINT_GOOGLE_CLOUD_PROJECT_ID": "demo-project",
            "VISUALSPRINT_ACTION_ENGINE_RESOURCE_NAME": "projects/demo/locations/us-central1/reasoningEngines/action789",
            "VISUALSPRINT_REASONING_ENGINE_RESOURCE_NAME": "projects/demo/locations/us-central1/reasoningEngines/reasoning123",
            "VISUALSPRINT_SUMMARY_ENGINE_RESOURCE_NAME": "projects/demo/locations/us-central1/reasoningEngines/summary456",
            "VISUALSPRINT_GOOGLE_API_ACCESS_TOKEN": "ya29.vertex-token",
        }
    )

    monkeypatch.setattr(reasoning_module, "settings", vertex_settings)
    monkeypatch.setattr(summary_module, "settings", vertex_settings)
    monkeypatch.setattr(
        reasoning_module,
        "invoke_reasoning_agent",
        lambda payload: ReasoningRunResponse(
            clientChunkId=payload.clientChunkId,
            decisions=[
                {
                    "title": "Adopt the Vertex AI runtime",
                    "rationale": "Vertex produced a structured decision.",
                    "speakerLabel": "ReasoningAgent",
                }
            ],
            commitments=[],
            blockers=[],
            openQuestions=[],
            memoryMatches=[],
            resolvedDecisionIds=[],
            resolvedCommitmentIds=[],
            resolvedBlockerIds=[],
            resolvedOpenQuestionIds=[],
        ),
    )
    monkeypatch.setattr(
        summary_module,
        "invoke_summary_agent",
        lambda payload: FinalReportDraft(
            meetingId=payload.meetingId,
            generatedAt="2026-06-08T11:00:00Z",
            executiveSummary="Vertex AI response summary.",
            decisions=payload.decisions,
            commitments=payload.commitments,
            blockers=payload.blockers,
            openQuestions=payload.openQuestions,
            memoryHighlights=payload.memoryHighlights,
        ),
    )

    reasoning_module.run_reasoning_agent(
        ChunkInsightRequest(
            meetingId="mtg_vertex_001",
            meetingTitle="Vertex sync",
            meetingNotes="",
            clientChunkId="client-chunk-vertex-001",
            focusSummary="Vertex AI path should be used first.",
            attentionFlags=[],
            reasoningChecklist=[],
            focusAreas=[],
        )
    )
    summary_module.run_summary_agent(
        SummaryPacketRequest(
            meetingId="mtg_vertex_001",
            meetingTitle="Vertex sync",
            meetingStatus="ended",
            draftExecutiveSummary="Vertex summary path.",
            decisions=[],
            commitments=[],
            blockers=[],
            openQuestions=[],
            memoryHighlights=[],
        )
    )

    with TestClient(app) as client:
        audit_response = client.get("/api/audit/invocations")
        audit_payload = audit_response.json()
        assert audit_payload["summary"]["bridgeRuns"] == 0
        assert audit_payload["summary"]["bridgeFallbackRuns"] == 0
        assert audit_payload["summary"]["mockRuns"] == 0
        assert audit_payload["invocations"][0]["executionMode"] == "vertex_ai"
        assert audit_payload["invocations"][1]["executionMode"] == "vertex_ai"


def test_configured_cloud_reasoning_and_summary_use_bridge_before_fallback(monkeypatch):
    bridge_settings = build_settings(
        {
            "VISUALSPRINT_AGENT_MODE": "configured_cloud",
            "VISUALSPRINT_GOOGLE_CLOUD_PROJECT_ID": "demo-project",
            "VISUALSPRINT_ACTION_AGENT_ID": "action-agent",
            "VISUALSPRINT_REASONING_AGENT_ID": "reasoning-agent",
            "VISUALSPRINT_SUMMARY_AGENT_ID": "summary-agent",
            "VISUALSPRINT_ACTION_AGENT_ENDPOINT_URL": "https://agents.example/action",
            "VISUALSPRINT_REASONING_AGENT_ENDPOINT_URL": "https://agents.example/reasoning",
            "VISUALSPRINT_SUMMARY_AGENT_ENDPOINT_URL": "https://agents.example/summary",
        }
    )

    monkeypatch.setattr(reasoning_module, "settings", bridge_settings)
    monkeypatch.setattr(summary_module, "settings", bridge_settings)
    monkeypatch.setattr(
        reasoning_module,
        "invoke_reasoning_agent",
        lambda payload: ReasoningRunResponse(
            clientChunkId=payload.clientChunkId,
            decisions=[
                {
                    "title": "Use the configured bridge",
                    "rationale": "Bridge produced a structured decision.",
                    "speakerLabel": "ReasoningAgent",
                }
            ],
            commitments=[],
            blockers=[],
            openQuestions=[],
            memoryMatches=[],
            resolvedDecisionIds=[],
            resolvedCommitmentIds=[],
            resolvedBlockerIds=[],
            resolvedOpenQuestionIds=[],
        ),
    )
    monkeypatch.setattr(
        summary_module,
        "invoke_summary_agent",
        lambda payload: FinalReportDraft(
            meetingId=payload.meetingId,
            generatedAt="2026-06-07T10:00:00Z",
            executiveSummary="Bridge response summary.",
            decisions=payload.decisions,
            commitments=payload.commitments,
            blockers=payload.blockers,
            openQuestions=payload.openQuestions,
            memoryHighlights=payload.memoryHighlights,
        ),
    )

    reasoning_response = reasoning_module.run_reasoning_agent(
        ChunkInsightRequest(
            meetingId="mtg_bridge_001",
            meetingTitle="Bridge sync",
            meetingNotes="",
            clientChunkId="client-chunk-bridge-001",
            focusSummary="Bridge path should be used first.",
            attentionFlags=[],
            reasoningChecklist=[],
            focusAreas=[],
        )
    )
    assert reasoning_response.clientChunkId == "client-chunk-bridge-001"

    summary_response = summary_module.run_summary_agent(
        SummaryPacketRequest(
            meetingId="mtg_bridge_001",
            meetingTitle="Bridge sync",
            meetingStatus="ended",
            draftExecutiveSummary="Bridge path summary.",
            decisions=[],
            commitments=[],
            blockers=[],
            openQuestions=[],
            memoryHighlights=[],
        )
    )
    assert summary_response.executiveSummary == "Bridge response summary."

    with TestClient(app) as client:
        audit_response = client.get("/api/audit/invocations")
        audit_payload = audit_response.json()
        assert audit_payload["summary"]["bridgeRuns"] == 2
        assert audit_payload["summary"]["mockRuns"] == 0
        assert audit_payload["summary"]["bridgeFallbackRuns"] == 0
        assert all(item["executionMode"] == "bridge" for item in audit_payload["invocations"])


def test_configured_cloud_falls_back_when_bridge_returns_none(monkeypatch):
    bridge_settings = build_settings(
        {
            "VISUALSPRINT_AGENT_MODE": "configured_cloud",
            "VISUALSPRINT_GOOGLE_CLOUD_PROJECT_ID": "demo-project",
            "VISUALSPRINT_ACTION_AGENT_ID": "action-agent",
            "VISUALSPRINT_REASONING_AGENT_ID": "reasoning-agent",
            "VISUALSPRINT_SUMMARY_AGENT_ID": "summary-agent",
            "VISUALSPRINT_ACTION_AGENT_ENDPOINT_URL": "https://agents.example/action",
            "VISUALSPRINT_REASONING_AGENT_ENDPOINT_URL": "https://agents.example/reasoning",
            "VISUALSPRINT_SUMMARY_AGENT_ENDPOINT_URL": "https://agents.example/summary",
        }
    )

    monkeypatch.setattr(reasoning_module, "settings", bridge_settings)
    monkeypatch.setattr(summary_module, "settings", bridge_settings)
    monkeypatch.setattr(reasoning_module, "invoke_reasoning_agent", lambda payload: None)
    monkeypatch.setattr(summary_module, "invoke_summary_agent", lambda payload: None)

    reasoning_response = reasoning_module.run_reasoning_agent(
        ChunkInsightRequest(
            meetingId="mtg_fallback_001",
            meetingTitle="Fallback sync",
            meetingNotes="",
            clientChunkId="client-chunk-fallback-001",
            focusSummary="Fallback path should produce a deterministic decision.",
            attentionFlags=[],
            reasoningChecklist=[],
            focusAreas=[],
        )
    )
    assert len(reasoning_response.decisions) == 1

    summary_response = summary_module.run_summary_agent(
        SummaryPacketRequest(
            meetingId="mtg_fallback_001",
            meetingTitle="Fallback sync",
            meetingStatus="ended",
            draftExecutiveSummary="Fallback summary path.",
            decisions=[],
            commitments=[],
            blockers=[],
            openQuestions=[],
            memoryHighlights=[],
        )
    )
    assert "Fallback summary path." in summary_response.executiveSummary

    with TestClient(app) as client:
        audit_response = client.get("/api/audit/invocations")
        audit_payload = audit_response.json()
        assert audit_payload["summary"]["bridgeFallbackRuns"] == 2
        assert audit_payload["summary"]["mockRuns"] == 0
        assert audit_payload["summary"]["bridgeRuns"] == 0
        assert all(
            item["executionMode"] == "bridge_fallback"
            for item in audit_payload["invocations"]
        )


def test_agent_eval_fixtures_load_and_cover_reasoning_and_summary():
    reasoning_fixtures = load_reasoning_eval_fixtures()
    summary_fixtures = load_summary_eval_fixtures()

    assert len(reasoning_fixtures) >= 6
    assert len(summary_fixtures) >= 2
    assert any(fixture.fixtureId == "reasoning_new_decision" for fixture in reasoning_fixtures)
    assert any(fixture.fixtureId == "summary_closed_meeting_report" for fixture in summary_fixtures)


def test_agent_eval_smoke_runner_passes_fixture_set():
    results = run_agent_eval_smoke()

    assert len(results) >= 8
    assert all(result.passed for result in results)
