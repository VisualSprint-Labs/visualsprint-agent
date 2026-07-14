"""Lightweight Elastic MCP client for the VisualSprint agents service."""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib import error, request

from visualsprint_agents.config import settings

logger = logging.getLogger("visualsprint_agents.elastic_mcp")

_MCP_ACCEPT = "application/json, text/event-stream"


def call_search_prior_outcomes_tool(
    *,
    record_type: str,
    summary: str,
    detail: str,
    tenant_id: str = "default",
    meeting_id: str = "",
) -> dict[str, Any]:
    if not settings.elastic_mcp_endpoint:
        return _not_configured(
            record_type=record_type,
            summary=summary,
            detail=detail,
            tenant_id=tenant_id,
            meeting_id=meeting_id,
            note="Elastic MCP endpoint is not configured for this agents service runtime.",
        )
    if not settings.elastic_api_key:
        return _not_configured(
            record_type=record_type,
            summary=summary,
            detail=detail,
            tenant_id=tenant_id,
            meeting_id=meeting_id,
            note=(
                "Elastic MCP endpoint is configured, but a runtime API key value is not present. "
                "Set VISUALSPRINT_ELASTIC_API_KEY for direct MCP calls in this environment."
            ),
        )

    init_body, init_headers = _mcp_request(
        method="initialize",
        params={
            "capabilities": {},
            "clientInfo": {
                "name": "visualsprint-agents",
                "version": settings.version,
            },
            "protocolVersion": "2024-11-05",
        },
        request_id=1,
    )
    if init_body is None:
        return _unavailable(
            record_type=record_type,
            summary=summary,
            detail=detail,
            tenant_id=tenant_id,
            meeting_id=meeting_id,
            note="Elastic MCP initialize request failed; no historical matches were returned.",
        )

    session_id = init_headers.get("Mcp-Session-Id")
    if session_id:
        _mcp_notify(
            method="notifications/initialized",
            session_id=session_id,
        )

    extra_headers: dict[str, str] | None = (
        {"Mcp-Session-Id": session_id} if session_id else None
    )
    tool_body, _ = _mcp_request(
        method="tools/call",
        params={
            "name": "search_prior_outcomes",
            "arguments": {
                "recordType": record_type,
                "summary": summary,
                "detail": detail,
                "tenantId": tenant_id,
                "meetingId": meeting_id,
            },
        },
        request_id=2,
        extra_headers=extra_headers,
    )
    if tool_body is None:
        return _unavailable(
            record_type=record_type,
            summary=summary,
            detail=detail,
            tenant_id=tenant_id,
            meeting_id=meeting_id,
            note="Elastic MCP tool invocation failed; no historical matches were returned.",
        )

    parsed = _extract_tool_matches(tool_body)
    if parsed is None:
        return _unavailable(
            record_type=record_type,
            summary=summary,
            detail=detail,
            tenant_id=tenant_id,
            meeting_id=meeting_id,
            note="Elastic MCP returned an unexpected tool payload shape.",
        )

    matches = parsed.get("matches", [])
    note = parsed.get(
        "note",
        "Elastic MCP search returned ranked historical candidates for the reasoning flow.",
    )
    return {
        "status": "ok",
        "recordType": record_type,
        "summary": summary,
        "detail": detail,
        "tenantId": tenant_id,
        "meetingId": meeting_id,
        "matches": matches if isinstance(matches, list) else [],
        "note": note,
    }


def _mcp_request(
    *,
    method: str,
    params: dict[str, Any],
    request_id: int,
    extra_headers: dict[str, str] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, str]]:
    """Send a JSON-RPC request and return (body, response_headers)."""
    if not settings.elastic_mcp_endpoint or not settings.elastic_api_key:
        return None, {}

    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params,
    }
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": _MCP_ACCEPT,
        "Authorization": f"ApiKey {settings.elastic_api_key}",
    }
    if extra_headers:
        headers.update(extra_headers)
    try:
        response = request.urlopen(
            request.Request(
                url=settings.elastic_mcp_endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            ),
            timeout=settings.agent_request_timeout_seconds,
        )
        response_headers = {k: v for k, v in response.headers.items()}
        body = _parse_mcp_response(response)
        return body, response_headers
    except error.HTTPError as exc:
        logger.warning("MCP %s request returned HTTP %s", method, exc.code)
        return None, {}
    except (error.URLError, TimeoutError) as exc:
        logger.warning("MCP %s request failed: %s", method, exc)
        return None, {}
    except Exception as exc:
        logger.warning("MCP %s request raised: %s", method, exc)
        return None, {}


def _mcp_notify(*, method: str, session_id: str) -> None:
    """Send a fire-and-forget MCP notification (no response expected)."""
    if not settings.elastic_mcp_endpoint or not settings.elastic_api_key:
        return
    payload = {"jsonrpc": "2.0", "method": method}
    headers = {
        "Content-Type": "application/json",
        "Accept": _MCP_ACCEPT,
        "Authorization": f"ApiKey {settings.elastic_api_key}",
        "Mcp-Session-Id": session_id,
    }
    try:
        request.urlopen(
            request.Request(
                url=settings.elastic_mcp_endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            ),
            timeout=min(settings.agent_request_timeout_seconds, 5.0),
        )
    except Exception:
        pass


def _parse_mcp_response(response) -> dict[str, Any] | None:
    """Parse a JSON-RPC response body, handling both JSON and SSE."""
    content_type = response.headers.get("Content-Type", "")
    raw = response.read().decode("utf-8")
    if "text/event-stream" in content_type:
        return _parse_sse_payload(raw)
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("MCP response was not valid JSON")
        return None
    return decoded if isinstance(decoded, dict) else None


def _parse_sse_payload(raw: str) -> dict[str, Any] | None:
    """Extract the first JSON-RPC message from an SSE stream."""
    for block in raw.split("\n\n"):
        for line in block.strip().splitlines():
            if line.startswith("data:"):
                data = line[5:].strip()
                if not data:
                    continue
                try:
                    decoded = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if isinstance(decoded, dict):
                    return decoded
    return None


def _extract_tool_matches(response: dict[str, Any]) -> dict[str, Any] | None:
    result = response.get("result")
    if isinstance(result, dict):
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            return structured
        content = result.get("content")
        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict):
                    continue
                text = item.get("text")
                if not isinstance(text, str) or not text.strip():
                    continue
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    return parsed
    return None


def _not_configured(
    *,
    record_type: str,
    summary: str,
    detail: str,
    tenant_id: str,
    meeting_id: str,
    note: str,
) -> dict[str, Any]:
    return {
        "status": "not_configured",
        "recordType": record_type,
        "summary": summary,
        "detail": detail,
        "tenantId": tenant_id,
        "meetingId": meeting_id,
        "matches": [],
        "note": note,
    }


def _unavailable(
    *,
    record_type: str,
    summary: str,
    detail: str,
    tenant_id: str,
    meeting_id: str,
    note: str,
) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "recordType": record_type,
        "summary": summary,
        "detail": detail,
        "tenantId": tenant_id,
        "meetingId": meeting_id,
        "matches": [],
        "note": note,
    }
