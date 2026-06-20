"""Vertex Agent Engine wrappers that expose query() for the Cloud Run adapter."""

from __future__ import annotations

import json
import uuid
from typing import Any, Callable, TypeVar

from pydantic import BaseModel, ValidationError

from visualsprint_agents.adk.action_agent import build_action_root_agent
from visualsprint_agents.adk.reasoning_agent import build_reasoning_root_agent
from visualsprint_agents.adk.summary_agent import build_summary_root_agent
from visualsprint_agents.models import (
    ActionAgentRequest,
    ActionAgentResponse,
    ChunkInsightRequest,
    FinalReportDraft,
    ReasoningRunResponse,
    SummaryPacketRequest,
)

T = TypeVar("T", bound=BaseModel)
CoalesceFn = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]


def register_query_operations() -> dict[str, list[str]]:
    return {"": ["query"]}


def _strip_code_fences(value: str) -> str:
    candidate = value.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()
    return candidate


def _try_parse_json(value: str) -> dict[str, Any] | None:
    candidate = _strip_code_fences(value)
    if not candidate:
        return None
    # 1. Direct parse.
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    # 2. Prose-wrapped JSON: parse the first {...} object substring.
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def _extract_text_from_event(event: Any) -> list[str]:
    texts: list[str] = []
    content = getattr(event, "content", None)
    parts = getattr(content, "parts", None) if content is not None else None
    if not parts:
        return texts
    for part in parts:
        text = getattr(part, "text", None)
        if isinstance(text, str) and text.strip():
            texts.append(text.strip())
    return texts


def _extract_function_call_args(event: Any) -> list[dict[str, Any]]:
    if not hasattr(event, "get_function_calls"):
        return []
    args_list: list[dict[str, Any]] = []
    for call in event.get_function_calls():
        fn_args = getattr(call, "args", None)
        if isinstance(fn_args, dict):
            args_list.append(fn_args)
    return args_list


def _extract_function_response_dicts(event: Any) -> list[dict[str, Any]]:
    if not hasattr(event, "get_function_responses"):
        return []
    responses: list[dict[str, Any]] = []
    for fn_response in event.get_function_responses():
        response = getattr(fn_response, "response", None)
        if isinstance(response, dict):
            responses.append(response)
    return responses


def _extract_state_delta_values(event: Any, output_key: str | None) -> list[Any]:
    if not output_key:
        return []
    actions = getattr(event, "actions", None)
    state_delta = getattr(actions, "state_delta", None) if actions is not None else None
    if isinstance(state_delta, dict) and output_key in state_delta:
        return [state_delta[output_key]]
    return []


def _normalize_to_dict(candidate: Any) -> dict[str, Any] | None:
    if isinstance(candidate, dict):
        return candidate
    if isinstance(candidate, str):
        return _try_parse_json(candidate)
    return None


def _coalesce_reasoning_output(
    input_payload: dict[str, Any],
    parsed: dict[str, Any],
) -> dict[str, Any]:
    if "payload" in parsed and isinstance(parsed["payload"], dict):
        parsed = dict(parsed["payload"])
    parsed.setdefault("clientChunkId", input_payload.get("clientChunkId", ""))
    for key in (
        "decisions",
        "commitments",
        "blockers",
        "openQuestions",
        "memoryMatches",
        "resolvedDecisionIds",
        "resolvedCommitmentIds",
        "resolvedBlockerIds",
        "resolvedOpenQuestionIds",
    ):
        parsed.setdefault(key, [])
    return parsed


def _coalesce_summary_output(
    input_payload: dict[str, Any],
    parsed: dict[str, Any],
) -> dict[str, Any]:
    if "report" in parsed and isinstance(parsed["report"], dict):
        parsed = dict(parsed["report"])
    parsed.setdefault("meetingId", input_payload.get("meetingId", ""))
    for key in (
        "decisions",
        "commitments",
        "blockers",
        "openQuestions",
        "memoryHighlights",
    ):
        parsed.setdefault(key, [])
    parsed.setdefault("executiveSummary", input_payload.get("draftExecutiveSummary", ""))
    parsed.setdefault("generatedAt", "2026-01-01T00:00:00Z")
    return parsed


def _coalesce_action_output(
    input_payload: dict[str, Any],
    parsed: dict[str, Any],
) -> dict[str, Any]:
    parsed.setdefault("meetingId", input_payload.get("meetingId", ""))
    parsed.setdefault("recommendations", parsed.get("recommendations", []))
    return parsed


def _coalesce_and_validate(
    candidate: dict[str, Any],
    *,
    output_model: type[T],
    input_payload: dict[str, Any],
    coalesce: CoalesceFn,
) -> dict[str, Any] | None:
    try:
        merged = coalesce(input_payload, dict(candidate))
        return output_model.model_validate(merged).model_dump(mode="json")
    except (ValidationError, ValueError, TypeError):
        return None


def _extract_structured_output(
    events: list[Any],
    *,
    output_model: type[T],
    input_payload: dict[str, Any],
    coalesce: CoalesceFn,
    output_key: str | None = None,
) -> dict[str, Any]:
    texts: list[str] = []
    tool_arg_candidates: list[dict[str, Any]] = []
    tool_response_candidates: list[dict[str, Any]] = []
    state_candidates: list[Any] = []

    for event in events:
        texts.extend(_extract_text_from_event(event))
        tool_arg_candidates.extend(_extract_function_call_args(event))
        tool_response_candidates.extend(_extract_function_response_dicts(event))
        state_candidates.extend(_extract_state_delta_values(event, output_key))

    # 1. Agent output stored in session state under the configured output_key.
    for state_value in reversed(state_candidates):
        parsed = _normalize_to_dict(state_value)
        if parsed is not None:
            result = _coalesce_and_validate(
                parsed, output_model=output_model, input_payload=input_payload, coalesce=coalesce
            )
            if result is not None:
                return result

    # 2. Final-response text (handles direct JSON and prose-wrapped JSON).
    for text in reversed(texts):
        parsed = _try_parse_json(text)
        if parsed is not None:
            result = _coalesce_and_validate(
                parsed, output_model=output_model, input_payload=input_payload, coalesce=coalesce
            )
            if result is not None:
                return result

    # 3. Tool-call args (e.g. finalize_report / register_outputs / create_action_recommendations).
    for args in reversed(tool_arg_candidates):
        result = _coalesce_and_validate(
            args, output_model=output_model, input_payload=input_payload, coalesce=coalesce
        )
        if result is not None:
            return result

    # 4. Tool responses, in case the structured payload comes back from the tool.
    for response in reversed(tool_response_candidates):
        result = _coalesce_and_validate(
            response, output_model=output_model, input_payload=input_payload, coalesce=coalesce
        )
        if result is not None:
            return result

    # Nothing matched: raise with a bounded diagnostic so a failed run is debuggable
    # from the Vertex response body instead of being opaque.
    diagnostic = {
        "textSamples": [text[:240] for text in texts[:3]],
        "toolCallKeys": [sorted(args.keys()) for args in tool_arg_candidates[:3]],
        "toolResponseKeys": [sorted(resp.keys()) for resp in tool_response_candidates[:3]],
        "stateKeyPresent": bool(state_candidates),
        "eventCount": len(events),
    }
    raise ValueError(
        f"Unable to extract {output_model.__name__} from ADK events. Diagnostic: "
        f"{json.dumps(diagnostic)}"
    )


def _run_coroutine_blocking(coro: Any) -> Any:
    """Run a coroutine to completion even when an event loop is already running.

    Agent Engine serves requests inside a running event loop, so ``asyncio.run``
    cannot be used directly. We execute the coroutine on a dedicated thread with
    its own loop and re-raise any exception (the prior sync ``Runner.run`` path
    swallowed agent errors, which surfaced as zero events).
    """
    import asyncio
    import concurrent.futures

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


async def _collect_adk_events(
    *,
    root_agent: object,
    app_name: str,
    input_payload: dict[str, Any],
) -> list[Any]:
    from google.adk.runners import Runner
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.genai import types

    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name=app_name,
        session_service=session_service,
    )
    user_id = "visualsprint-engine"
    session_id = str(uuid.uuid4())
    # create_session is async; awaiting it is required or no session exists and
    # the run yields zero events.
    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )
    message = types.Content(
        role="user",
        parts=[types.Part(text=json.dumps(input_payload))],
    )
    events: list[Any] = []
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=message,
    ):
        events.append(event)
    return events


def run_structured_adk_query(
    *,
    root_agent: object,
    app_name: str,
    input_payload: dict[str, Any],
    output_model: type[T],
    coalesce: CoalesceFn,
) -> dict[str, Any]:
    events = _run_coroutine_blocking(
        _collect_adk_events(
            root_agent=root_agent,
            app_name=app_name,
            input_payload=input_payload,
        )
    )
    output_key = getattr(root_agent, "output_key", None)
    return _extract_structured_output(
        events,
        output_model=output_model,
        input_payload=input_payload,
        coalesce=coalesce,
        output_key=output_key,
    )


class VisualSprintReasoningEngine:
    """Agent Engine runtime wrapper for chunk-level reasoning."""

    def __init__(self) -> None:
        self._root_agent = build_reasoning_root_agent()

    def clone(self) -> VisualSprintReasoningEngine:
        return VisualSprintReasoningEngine()

    def register_operations(self) -> dict[str, list[str]]:
        return register_query_operations()

    def query(
        self,
        *,
        meetingId: str,
        meetingTitle: str,
        clientChunkId: str,
        focusSummary: str,
        meetingNotes: str = "",
        attentionFlags: list | None = None,
        reasoningChecklist: list | None = None,
        focusAreas: list | None = None,
        memoryMatches: list | None = None,
        transcriptSegments: list | None = None,
        screenEvents: list | None = None,
        **_ignored: Any,
    ) -> dict:
        payload = {
            "meetingId": meetingId,
            "meetingTitle": meetingTitle,
            "meetingNotes": meetingNotes,
            "clientChunkId": clientChunkId,
            "focusSummary": focusSummary,
            "attentionFlags": attentionFlags or [],
            "reasoningChecklist": reasoningChecklist or [],
            "focusAreas": focusAreas or [],
            "memoryMatches": memoryMatches or [],
            "transcriptSegments": transcriptSegments or [],
            "screenEvents": screenEvents or [],
        }
        validated = ChunkInsightRequest.model_validate(payload)
        serialized = validated.model_dump(mode="json")
        return run_structured_adk_query(
            root_agent=self._root_agent,
            app_name="visualsprint_reasoning_agent",
            input_payload=serialized,
            output_model=ReasoningRunResponse,
            coalesce=_coalesce_reasoning_output,
        )


class VisualSprintSummaryEngine:
    """Agent Engine runtime wrapper for final meeting summaries."""

    def __init__(self) -> None:
        self._root_agent = build_summary_root_agent()

    def clone(self) -> VisualSprintSummaryEngine:
        return VisualSprintSummaryEngine()

    def register_operations(self) -> dict[str, list[str]]:
        return register_query_operations()

    def query(
        self,
        *,
        meetingId: str,
        meetingTitle: str,
        meetingStatus: str,
        draftExecutiveSummary: str,
        decisions: list | None = None,
        commitments: list | None = None,
        blockers: list | None = None,
        openQuestions: list | None = None,
        memoryHighlights: list | None = None,
        **_ignored: Any,
    ) -> dict:
        payload = {
            "meetingId": meetingId,
            "meetingTitle": meetingTitle,
            "meetingStatus": meetingStatus,
            "draftExecutiveSummary": draftExecutiveSummary,
            "decisions": decisions or [],
            "commitments": commitments or [],
            "blockers": blockers or [],
            "openQuestions": openQuestions or [],
            "memoryHighlights": memoryHighlights or [],
        }
        validated = SummaryPacketRequest.model_validate(payload)
        serialized = validated.model_dump(mode="json")
        return run_structured_adk_query(
            root_agent=self._root_agent,
            app_name="visualsprint_summary_agent",
            input_payload=serialized,
            output_model=FinalReportDraft,
            coalesce=_coalesce_summary_output,
        )


class VisualSprintActionEngine:
    """Agent Engine runtime wrapper for action recommendations."""

    def __init__(self) -> None:
        self._root_agent = build_action_root_agent()

    def clone(self) -> VisualSprintActionEngine:
        return VisualSprintActionEngine()

    def register_operations(self) -> dict[str, list[str]]:
        return register_query_operations()

    def query(
        self,
        *,
        meetingId: str,
        meetingTitle: str,
        executiveSummary: str,
        decisions: list | None = None,
        commitments: list | None = None,
        blockers: list | None = None,
        openQuestions: list | None = None,
        **_ignored: Any,
    ) -> dict:
        payload = {
            "meetingId": meetingId,
            "meetingTitle": meetingTitle,
            "executiveSummary": executiveSummary,
            "decisions": decisions or [],
            "commitments": commitments or [],
            "blockers": blockers or [],
            "openQuestions": openQuestions or [],
        }
        validated = ActionAgentRequest.model_validate(payload)
        serialized = validated.model_dump(mode="json")
        return run_structured_adk_query(
            root_agent=self._root_agent,
            app_name="visualsprint_action_agent",
            input_payload=serialized,
            output_model=ActionAgentResponse,
            coalesce=_coalesce_action_output,
        )
