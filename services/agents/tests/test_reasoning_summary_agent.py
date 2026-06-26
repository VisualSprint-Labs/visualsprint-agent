from __future__ import annotations

import visualsprint_agents.reasoning as reasoning_module
import visualsprint_agents.summary as summary_module
from visualsprint_agents.config import build_settings
from visualsprint_agents.invocation_audit import audit_store
from visualsprint_agents.models import (
    ChunkInsightRequest,
    FinalReportDraft,
    ReasoningRunResponse,
    SummaryPacketRequest,
)


def _cloud_settings():
    return build_settings(
        {
            "VISUALSPRINT_AGENT_MODE": "configured_cloud",
            "VISUALSPRINT_AGENT_RUNTIME_BACKEND": "vertex_ai_reasoning_engine",
            "VISUALSPRINT_DEPLOYMENT_TARGET": "cloud_run",
            "VISUALSPRINT_GOOGLE_CLOUD_PROJECT_ID": "demo-project",
            "VISUALSPRINT_ACTION_ENGINE_RESOURCE_NAME": "projects/demo/locations/us-central1/reasoningEngines/action789",
            "VISUALSPRINT_REASONING_ENGINE_RESOURCE_NAME": "projects/demo/locations/us-central1/reasoningEngines/reasoning123",
            "VISUALSPRINT_SUMMARY_ENGINE_RESOURCE_NAME": "projects/demo/locations/us-central1/reasoningEngines/summary456",
        }
    )


def _configure_reasoning_cloud(monkeypatch) -> None:
    monkeypatch.setattr(reasoning_module, "settings", _cloud_settings())
    audit_store.clear()


def _configure_summary_cloud(monkeypatch) -> None:
    monkeypatch.setattr(summary_module, "settings", _cloud_settings())
    audit_store.clear()


def _reasoning_payload() -> ChunkInsightRequest:
    return ChunkInsightRequest(
        meetingId="mtg_reasoning_001",
        meetingTitle="Release readiness sync",
        meetingNotes="",
        clientChunkId="client-chunk-001",
        focusSummary="The team needs to confirm rollback readiness.",
        attentionFlags=[],
        reasoningChecklist=[],
        focusAreas=[],
    )


def _summary_payload() -> SummaryPacketRequest:
    return SummaryPacketRequest(
        meetingId="mtg_summary_001",
        meetingTitle="Release readiness sync",
        meetingStatus="ended",
        draftExecutiveSummary="Draft summary.",
        decisions=[],
        commitments=[],
        blockers=[],
        openQuestions=[],
        memoryHighlights=[],
    )


def _vertex_reasoning_response(payload: ChunkInsightRequest) -> ReasoningRunResponse:
    return ReasoningRunResponse(
        clientChunkId=payload.clientChunkId,
        decisions=[
            {
                "title": "Confirm rollback readiness before deploy",
                "rationale": "Rollback readiness must be explicit.",
                "speakerLabel": "ReasoningAgent",
            }
        ],
        commitments=[],
        blockers=[],
        openQuestions=[],
        memoryMatches=[],
    )


def _empty_reasoning_response(payload: ChunkInsightRequest) -> ReasoningRunResponse:
    return ReasoningRunResponse(
        clientChunkId=payload.clientChunkId,
        decisions=[],
        commitments=[],
        blockers=[],
        openQuestions=[],
        memoryMatches=[],
    )


def test_reasoning_vertex_with_content_skips_fallback(monkeypatch):
    _configure_reasoning_cloud(monkeypatch)
    monkeypatch.setattr(
        reasoning_module, "invoke_reasoning_agent", _vertex_reasoning_response
    )

    response = reasoning_module.run_reasoning_agent(_reasoning_payload())

    assert len(response.decisions) == 1
    assert response.decisions[0].title == "Confirm rollback readiness before deploy"
    assert audit_store.snapshot()[0].execution_mode == "vertex_ai"
    assert audit_store.snapshot()[0].status == "success"


def test_reasoning_vertex_empty_returns_empty_response(monkeypatch):
    _configure_reasoning_cloud(monkeypatch)
    monkeypatch.setattr(
        reasoning_module, "invoke_reasoning_agent", _empty_reasoning_response
    )

    response = reasoning_module.run_reasoning_agent(_reasoning_payload())

    assert not (response.decisions or response.commitments or response.blockers)
    assert response.clientChunkId == _reasoning_payload().clientChunkId
    assert audit_store.snapshot()[0].execution_mode == "vertex_ai_fallback"
    assert audit_store.snapshot()[0].status == "fallback"
    assert "returned no reasoning output" in audit_store.snapshot()[0].detail


def test_reasoning_vertex_failure_returns_empty_response(monkeypatch):
    _configure_reasoning_cloud(monkeypatch)
    monkeypatch.setattr(reasoning_module, "invoke_reasoning_agent", lambda payload: None)

    response = reasoning_module.run_reasoning_agent(_reasoning_payload())

    assert not (response.decisions or response.commitments or response.blockers)
    assert response.clientChunkId == _reasoning_payload().clientChunkId
    assert audit_store.snapshot()[0].execution_mode == "vertex_ai_fallback"
    assert audit_store.snapshot()[0].status == "fallback"
    assert "unavailable" in audit_store.snapshot()[0].detail


def test_summary_vertex_with_content_skips_fallback(monkeypatch):
    _configure_summary_cloud(monkeypatch)
    monkeypatch.setattr(
        summary_module,
        "invoke_summary_agent",
        lambda payload: FinalReportDraft(
            meetingId=payload.meetingId,
            generatedAt="2026-06-08T11:00:00Z",
            executiveSummary="A synthesized executive summary that adds new context.",
            decisions=payload.decisions,
            commitments=payload.commitments,
            blockers=payload.blockers,
            openQuestions=payload.openQuestions,
            memoryHighlights=payload.memoryHighlights,
        ),
    )

    response = summary_module.run_summary_agent(_summary_payload())

    assert response.executiveSummary == "A synthesized executive summary that adds new context."
    assert audit_store.snapshot()[0].execution_mode == "vertex_ai"
    assert audit_store.snapshot()[0].status == "success"


def test_summary_vertex_blank_uses_fallback(monkeypatch):
    _configure_summary_cloud(monkeypatch)
    monkeypatch.setattr(
        summary_module,
        "invoke_summary_agent",
        lambda payload: FinalReportDraft(
            meetingId=payload.meetingId,
            generatedAt="2026-06-08T11:00:00Z",
            executiveSummary="   ",
            decisions=payload.decisions,
            commitments=payload.commitments,
            blockers=payload.blockers,
            openQuestions=payload.openQuestions,
            memoryHighlights=payload.memoryHighlights,
        ),
    )

    response = summary_module.run_summary_agent(_summary_payload())

    assert response.executiveSummary.strip()
    assert audit_store.snapshot()[0].execution_mode == "vertex_ai_fallback"
    assert audit_store.snapshot()[0].status == "fallback"
    assert "no usable summary" in audit_store.snapshot()[0].detail


def test_summary_vertex_echoed_draft_uses_fallback(monkeypatch):
    _configure_summary_cloud(monkeypatch)
    monkeypatch.setattr(
        summary_module,
        "invoke_summary_agent",
        lambda payload: FinalReportDraft(
            meetingId=payload.meetingId,
            generatedAt="2026-06-08T11:00:00Z",
            executiveSummary=payload.draftExecutiveSummary,
            decisions=payload.decisions,
            commitments=payload.commitments,
            blockers=payload.blockers,
            openQuestions=payload.openQuestions,
            memoryHighlights=payload.memoryHighlights,
        ),
    )

    response = summary_module.run_summary_agent(_summary_payload())

    assert audit_store.snapshot()[0].execution_mode == "vertex_ai_fallback"
    assert audit_store.snapshot()[0].status == "fallback"


def test_summary_vertex_failure_uses_fallback(monkeypatch):
    _configure_summary_cloud(monkeypatch)
    monkeypatch.setattr(summary_module, "invoke_summary_agent", lambda payload: None)

    response = summary_module.run_summary_agent(_summary_payload())

    assert response.executiveSummary.strip()
    assert audit_store.snapshot()[0].execution_mode == "vertex_ai_fallback"
    assert audit_store.snapshot()[0].status == "fallback"
    assert "unavailable" in audit_store.snapshot()[0].detail
