"""Invocation bridge for configured cloud-agent execution."""

from __future__ import annotations

import json
import sys
from urllib import error, request

from visualsprint_agents.config import settings


def _log(msg: str) -> None:
    print(f"[agents] {msg}", file=sys.stderr, flush=True)
from visualsprint_agents.models import (
    ActionAgentRequest,
    ActionAgentResponse,
    FinalReportDraft,
    ReasoningRunResponse,
    SummaryPacketRequest,
    ChunkInsightRequest,
)
from visualsprint_agents.vertex_normalization import extract_vertex_structured_output


def invoke_reasoning_agent(payload: ChunkInsightRequest) -> ReasoningRunResponse | None:
    """Try the configured reasoning-agent bridge and return validated output."""

    response_payload: dict | None
    if settings.agent_runtime_backend == "vertex_ai_reasoning_engine":
        if not settings.cloud_adapter_ready or not settings.reasoning_engine_resource_name:
            return None
        response_payload = _query_vertex_reasoning_engine(
            resource_name=settings.reasoning_engine_resource_name,
            input_payload=payload.model_dump(mode="json"),
            query_url=settings.reasoning_query_url,
        )
        if response_payload is None:
            return None
        output_payload = extract_vertex_structured_output(response_payload)
        if output_payload is None:
            _log(f"Vertex reasoning: could not extract structured output from response: {str(response_payload)[:300]}")
            return None
        try:
            return ReasoningRunResponse.model_validate(output_payload)
        except ValueError as exc:
            _log(f"Vertex reasoning: ReasoningRunResponse validation failed — {exc}")
            return None

    if not settings.cloud_adapter_ready or not settings.reasoning_agent_endpoint_url:
        return None

    response_payload = _post_json(
        url=settings.reasoning_agent_endpoint_url,
        payload=payload.model_dump(mode="json"),
        target_agent_id=settings.reasoning_agent_id,
    )
    if response_payload is None:
        return None
    try:
        return ReasoningRunResponse.model_validate(response_payload)
    except ValueError:
        return None


def invoke_summary_agent(payload: SummaryPacketRequest) -> FinalReportDraft | None:
    """Try the configured summary-agent bridge and return validated output."""

    response_payload: dict | None
    if settings.agent_runtime_backend == "vertex_ai_reasoning_engine":
        if not settings.cloud_adapter_ready or not settings.summary_engine_resource_name:
            return None
        response_payload = _query_vertex_reasoning_engine(
            resource_name=settings.summary_engine_resource_name,
            input_payload=payload.model_dump(mode="json"),
            query_url=settings.summary_query_url,
        )
        if response_payload is None:
            return None
        output_payload = extract_vertex_structured_output(response_payload)
        if output_payload is None:
            return None
        try:
            return FinalReportDraft.model_validate(output_payload)
        except ValueError:
            return None

    if not settings.cloud_adapter_ready or not settings.summary_agent_endpoint_url:
        return None

    response_payload = _post_json(
        url=settings.summary_agent_endpoint_url,
        payload=payload.model_dump(mode="json"),
        target_agent_id=settings.summary_agent_id,
    )
    if response_payload is None:
        return None
    try:
        return FinalReportDraft.model_validate(response_payload)
    except ValueError:
        return None


def invoke_action_agent(payload: ActionAgentRequest) -> ActionAgentResponse | None:
    """Try the configured action-agent bridge and return validated output."""

    response_payload: dict | None
    if settings.agent_runtime_backend == "vertex_ai_reasoning_engine":
        if not settings.cloud_adapter_ready or not settings.action_engine_resource_name:
            return None
        response_payload = _query_vertex_reasoning_engine(
            resource_name=settings.action_engine_resource_name,
            input_payload=payload.model_dump(mode="json"),
            query_url=settings.action_query_url,
        )
        if response_payload is None:
            return None
        output_payload = extract_vertex_structured_output(response_payload)
        if output_payload is None:
            return None
        try:
            return ActionAgentResponse.model_validate(output_payload)
        except ValueError:
            return None

    if not settings.cloud_adapter_ready or not settings.action_agent_endpoint_url:
        return None

    response_payload = _post_json(
        url=settings.action_agent_endpoint_url,
        payload=payload.model_dump(mode="json"),
        target_agent_id=settings.action_agent_id,
    )
    if response_payload is None:
        return None
    try:
        return ActionAgentResponse.model_validate(response_payload)
    except ValueError:
        return None


def _post_json(
    *,
    url: str,
    payload: dict,
    target_agent_id: str | None,
) -> dict | None:
    headers = {
        "Content-Type": "application/json",
    }
    if settings.agent_bridge_bearer_token:
        headers["Authorization"] = f"Bearer {settings.agent_bridge_bearer_token}"
    if settings.google_cloud_project_id:
        headers["X-VisualSprint-Gcp-Project"] = settings.google_cloud_project_id
    if settings.google_cloud_location:
        headers["X-VisualSprint-Gcp-Location"] = settings.google_cloud_location
    if settings.agent_application_id:
        headers["X-VisualSprint-Agent-Application"] = settings.agent_application_id
    if target_agent_id:
        headers["X-VisualSprint-Agent-Id"] = target_agent_id

    try:
        response = request.urlopen(
            request.Request(
                url=url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            ),
            timeout=settings.agent_request_timeout_seconds,
        )
        return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        _log(f"bridge HTTP {exc.code} {exc.reason} — {body}")
        return None
    except error.URLError as exc:
        _log(f"bridge URL error — {exc.reason}")
        return None
    except json.JSONDecodeError as exc:
        _log(f"bridge JSON decode error — {exc}")
        return None


def _query_vertex_reasoning_engine(
    *,
    resource_name: str,
    input_payload: dict,
    query_url: str | None = None,
) -> dict | None:
    access_token = _resolve_google_access_token()
    if access_token is None:
        return None

    url = query_url or f"https://aiplatform.googleapis.com/v1/{resource_name}:query"
    body = {
        "classMethod": "query",
        "input": input_payload,
    }
    _log(f"Vertex query → {url}")
    try:
        response = request.urlopen(
            request.Request(
                url=url,
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                },
                method="POST",
            ),
            timeout=settings.agent_request_timeout_seconds,
        )
        result = json.loads(response.read().decode("utf-8"))
        _log(f"Vertex response keys: {list(result.keys())}")
        return result
    except error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")[:500]
        _log(f"Vertex HTTP {exc.code} {exc.reason} — {body_text}")
        return None
    except error.URLError as exc:
        _log(f"Vertex URL error — {exc.reason}")
        return None
    except json.JSONDecodeError as exc:
        _log(f"Vertex JSON decode error — {exc}")
        return None


def _resolve_google_access_token() -> str | None:
    if settings.google_api_access_token is not None:
        return settings.google_api_access_token
    if settings.deployment_target != "cloud_run":
        return None
    try:
        response = request.urlopen(
            request.Request(
                url=(
                    "http://metadata.google.internal/computeMetadata/v1/"
                    "instance/service-accounts/default/token"
                ),
                headers={"Metadata-Flavor": "Google"},
                method="GET",
            ),
            timeout=settings.agent_request_timeout_seconds,
        )
        payload = json.loads(response.read().decode("utf-8"))
        access_token = payload.get("access_token")
        return access_token if isinstance(access_token, str) and access_token else None
    except (error.URLError, error.HTTPError, json.JSONDecodeError):
        return None
