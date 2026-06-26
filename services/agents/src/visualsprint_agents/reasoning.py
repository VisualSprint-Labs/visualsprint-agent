"""Reasoning-agent adapter for VisualSprint."""

from __future__ import annotations

from visualsprint_agents.agent_runtime import invoke_reasoning_agent
from visualsprint_agents.config import settings
from visualsprint_agents.invocation_audit import audit_store
from visualsprint_agents.models import (
    AgentBlockerInput,
    AgentCommitmentInput,
    AgentDecisionInput,
    AgentMemoryMatchInput,
    AgentOpenQuestionInput,
    ChunkInsightRequest,
    ReasoningRunResponse,
)


def _reasoning_response_has_content(response: ReasoningRunResponse) -> bool:
    return bool(
        response.decisions
        or response.commitments
        or response.blockers
        or response.openQuestions
        or response.memoryMatches
        or response.resolvedDecisionIds
        or response.resolvedCommitmentIds
        or response.resolvedBlockerIds
        or response.resolvedOpenQuestionIds
    )


def _empty_reasoning_response(payload: ChunkInsightRequest) -> ReasoningRunResponse:
    """Return a schema-valid empty response so the caller can choose fallback."""

    return ReasoningRunResponse(clientChunkId=payload.clientChunkId)


def run_reasoning_agent(payload: ChunkInsightRequest) -> ReasoningRunResponse:
    """Generate reasoning outputs through the active adapter mode."""

    if settings.cloud_adapter_ready:
        cloud_response = invoke_reasoning_agent(payload)
        if cloud_response is not None and _reasoning_response_has_content(cloud_response):
            audit_store.record(
                agent_kind="reasoning",
                execution_mode=(
                    "vertex_ai"
                    if settings.agent_runtime_backend == "vertex_ai_reasoning_engine"
                    else "bridge"
                ),
                status="success",
                target_agent_id=(
                    settings.reasoning_engine_resource_name
                    if settings.agent_runtime_backend == "vertex_ai_reasoning_engine"
                    else settings.reasoning_agent_id
                ),
                request_key=payload.clientChunkId,
                detail=(
                    "Configured Vertex AI runtime produced the reasoning response."
                    if settings.agent_runtime_backend == "vertex_ai_reasoning_engine"
                    else "Configured bridge produced the reasoning response."
                ),
            )
            return cloud_response

        empty_cloud_response = (
            cloud_response is not None and not _reasoning_response_has_content(cloud_response)
        )
        is_vertex = settings.agent_runtime_backend == "vertex_ai_reasoning_engine"
        if is_vertex and empty_cloud_response:
            detail = "Configured Vertex AI runtime returned no reasoning output."
        elif is_vertex:
            detail = "Configured Vertex AI runtime was unavailable."
        elif empty_cloud_response:
            detail = "Configured bridge returned no reasoning output."
        else:
            detail = "Configured bridge was unavailable."

        audit_store.record(
            agent_kind="reasoning",
            execution_mode="vertex_ai_fallback" if is_vertex else "bridge_fallback",
            status="fallback",
            target_agent_id=(
                settings.reasoning_engine_resource_name
                if is_vertex
                else settings.reasoning_agent_id
            ),
            request_key=payload.clientChunkId,
            detail=detail,
        )

        # Vertex empty/failure is treated as a real "no durable signals" result so
        # the control plane does not hallucinate. Bridge failures fall back to the
        # deterministic template so the UI stays usable.
        if is_vertex:
            return _empty_reasoning_response(payload)
        return _run_mock_reasoning_agent(payload)

    audit_store.record(
        agent_kind="reasoning",
        execution_mode="mock",
        status="success",
        target_agent_id=None,
        request_key=payload.clientChunkId,
        detail="Deterministic mock reasoning path handled the request.",
    )
    return _run_mock_reasoning_agent(payload)


def _run_mock_reasoning_agent(payload: ChunkInsightRequest) -> ReasoningRunResponse:
    """Generate deterministic reasoning outputs from the assembled insight.

    Only used in mock mode for local development / unit tests.
    """

    decision_summary = (
        payload.focusAreas[0].summary if payload.focusAreas else payload.focusSummary
    )
    primary_detail = (
        payload.focusAreas[0].detail if payload.focusAreas else payload.focusSummary
    )
    decision = AgentDecisionInput(
        title=f"Decide on {decision_summary.lower()}",
        rationale=primary_detail,
        speakerLabel="ReasoningAgent",
    )

    commitment = AgentCommitmentInput(
        ownerLabel="Jordan",
        action="Publish the next-step handoff in the engineering channel",
        dueHint="Today",
    )

    blocker = AgentBlockerInput(
        summary="A recurring delivery risk still needs explicit owner confirmation.",
        severity="medium",
        ownerLabel="Mina",
    )

    open_question = AgentOpenQuestionInput(
        question="Which team confirms the final readiness gate before this topic is closed?",
        speakerLabel="ReasoningAgent",
    )

    memory_match = AgentMemoryMatchInput(
        sourceMeetingId=f"{payload.meetingId}_memory_stub",
        summary="A similar outcome appeared in a recent planning conversation.",
        sourceMeetingTitle=f"{payload.meetingTitle} memory context",
        strength="related",
        relation="recurring",
        score=0.71,
        snippet="A prior meeting raised a similar risk and required an explicit owner follow-up.",
    )

    return ReasoningRunResponse(
        clientChunkId=payload.clientChunkId,
        decisions=[decision],
        commitments=[commitment],
        blockers=[blocker],
        openQuestions=[open_question],
        memoryMatches=[memory_match],
    )
