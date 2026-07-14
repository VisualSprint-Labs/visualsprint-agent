"""Configuration for the VisualSprint agents service."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Literal, Mapping


AgentAdapterMode = Literal["mock", "configured_cloud"]
DeploymentTarget = Literal["local_dev", "cloud_run"]
AgentRuntimeBackend = Literal["bridge", "vertex_ai_reasoning_engine"]
DEFAULT_ADK_MODEL = "gemini-2.5-flash"


def _get(environ: Mapping[str, str], key: str) -> str | None:
    value = environ.get(key)
    return value.strip() if value and value.strip() else None


# Unfilled deployment-template placeholders that must never be treated as real
# resource names. Historically `VISUALSPRINT_REASONING_ENGINE_RESOURCE_NAME` shipped
# as ".../reasoningEngines/REASONING_ENGINE_ID" and shadowed the real alias below it,
# silently pointing the service at a non-existent engine.
_PLACEHOLDER_TOKENS = (
    "REASONING_ENGINE_ID",
    "SUMMARY_ENGINE_ID",
    "ACTION_ENGINE_ID",
)


def _is_placeholder(value: str) -> bool:
    return any(token in value for token in _PLACEHOLDER_TOKENS)


def _get_any(environ: Mapping[str, str], *keys: str) -> str | None:
    for key in keys:
        value = _get(environ, key)
        if value is not None and not _is_placeholder(value):
            return value
    return None


def _resolve_agent_mode(environ: Mapping[str, str]) -> AgentAdapterMode:
    raw_value = environ.get("VISUALSPRINT_AGENT_MODE", "").strip().lower()
    if raw_value == "configured_cloud":
        return "configured_cloud"
    return "mock"


def _resolve_deployment_target(environ: Mapping[str, str]) -> DeploymentTarget:
    raw_value = environ.get("VISUALSPRINT_DEPLOYMENT_TARGET", "").strip().lower()
    if raw_value == "cloud_run":
        return "cloud_run"
    return "local_dev"


def _resolve_agent_model(environ: Mapping[str, str], specific_key: str) -> str:
    specific = environ.get(specific_key, "").strip()
    if specific:
        return specific
    return environ.get("VISUALSPRINT_ADK_MODEL", "").strip() or DEFAULT_ADK_MODEL


def _resolve_allowed_origins(environ: Mapping[str, str]) -> tuple[str, ...]:
    raw_value = environ.get("VISUALSPRINT_ALLOWED_ORIGINS", "")
    if not raw_value.strip():
        return tuple()
    return tuple(
        origin.strip()
        for origin in raw_value.split(",")
        if origin.strip()
    )


def _resolve_agent_runtime_backend(environ: Mapping[str, str]) -> AgentRuntimeBackend:
    raw_value = environ.get("VISUALSPRINT_AGENT_RUNTIME_BACKEND", "").strip().lower()
    if raw_value == "vertex_ai_reasoning_engine":
        return "vertex_ai_reasoning_engine"
    return "bridge"


@dataclass(frozen=True, slots=True)
class Settings:
    service_name: str = "visualsprint-agents"
    version: str = "0.1.0"
    environment: str = "development"
    selected_track: str = "elastic"
    agent_mode: AgentAdapterMode = "mock"
    deployment_target: DeploymentTarget = "local_dev"
    agent_runtime_backend: AgentRuntimeBackend = "bridge"
    google_cloud_project_id: str | None = None
    google_cloud_project_number: str | None = None
    google_cloud_location: str | None = None
    agent_application_id: str | None = None
    reasoning_agent_id: str | None = None
    summary_agent_id: str | None = None
    action_agent_id: str | None = None
    reasoning_engine_resource_name: str | None = None
    summary_engine_resource_name: str | None = None
    action_engine_resource_name: str | None = None
    reasoning_agent_endpoint_url: str | None = None
    summary_agent_endpoint_url: str | None = None
    action_agent_endpoint_url: str | None = None
    reasoning_query_url: str | None = None
    summary_query_url: str | None = None
    action_query_url: str | None = None
    google_api_access_token: str | None = None
    agent_bridge_bearer_token: str | None = None
    agent_bridge_bearer_token_secret_name: str | None = None
    agent_runtime_service_account: str | None = None
    agent_request_timeout_seconds: float = 10.0
    elastic_mcp_endpoint: str | None = None
    elastic_api_key: str | None = None
    elastic_api_key_secret_name: str | None = None
    service_account_email: str | None = None
    cloud_run_service_url: str | None = None
    control_plane_url: str | None = None
    control_plane_bearer_token: str | None = None
    reasoning_model: str = DEFAULT_ADK_MODEL
    summary_model: str = DEFAULT_ADK_MODEL
    action_model: str = DEFAULT_ADK_MODEL
    allowed_origins: tuple[str, ...] = ()

    @property
    def reasoning_agent_configured(self) -> bool:
        return bool(self.google_cloud_project_id and self.reasoning_agent_id)

    @property
    def summary_agent_configured(self) -> bool:
        return bool(self.google_cloud_project_id and self.summary_agent_id)

    @property
    def action_agent_configured(self) -> bool:
        return bool(self.google_cloud_project_id and self.action_agent_id)

    @property
    def reasoning_endpoint_configured(self) -> bool:
        return self.reasoning_agent_endpoint_url is not None

    @property
    def summary_endpoint_configured(self) -> bool:
        return self.summary_agent_endpoint_url is not None

    @property
    def action_endpoint_configured(self) -> bool:
        return self.action_agent_endpoint_url is not None

    @property
    def bridge_auth_configured(self) -> bool:
        return bool(
            self.agent_bridge_bearer_token is not None
            or self.agent_bridge_bearer_token_secret_name is not None
        )

    @property
    def secret_manager_configured(self) -> bool:
        return self.agent_bridge_bearer_token_secret_name is not None

    @property
    def cloud_run_service_configured(self) -> bool:
        return self.cloud_run_service_url is not None

    @property
    def control_plane_configured(self) -> bool:
        return self.control_plane_url is not None

    @property
    def google_access_token_configured(self) -> bool:
        return self.google_api_access_token is not None

    @property
    def reasoning_engine_resource_configured(self) -> bool:
        return self.reasoning_engine_resource_name is not None

    @property
    def summary_engine_resource_configured(self) -> bool:
        return self.summary_engine_resource_name is not None

    @property
    def action_engine_resource_configured(self) -> bool:
        return self.action_engine_resource_name is not None

    @property
    def elastic_mcp_configured(self) -> bool:
        return bool(
            self.elastic_mcp_endpoint
            and (self.elastic_api_key is not None or self.elastic_api_key_secret_name is not None)
        )

    @property
    def cloud_adapter_ready(self) -> bool:
        if self.agent_runtime_backend == "vertex_ai_reasoning_engine":
            return (
                self.agent_mode == "configured_cloud"
                and self.google_cloud_project_id is not None
                and self.reasoning_engine_resource_configured
                and self.summary_engine_resource_configured
                and self.action_engine_resource_configured
                and (
                    self.google_access_token_configured
                    or self.deployment_target == "cloud_run"
                )
            )
        return (
            self.agent_mode == "configured_cloud"
            and self.reasoning_agent_configured
            and self.summary_agent_configured
            and self.action_agent_configured
            and self.reasoning_endpoint_configured
            and self.summary_endpoint_configured
            and self.action_endpoint_configured
        )

    @property
    def missing_cloud_configuration(self) -> tuple[str, ...]:
        missing: list[str] = []
        if self.agent_mode != "configured_cloud":
            return tuple(missing)
        if not self.google_cloud_project_id:
            missing.append("VISUALSPRINT_GOOGLE_CLOUD_PROJECT_ID")
        if self.agent_runtime_backend == "vertex_ai_reasoning_engine":
            if not self.reasoning_engine_resource_name:
                missing.append("VISUALSPRINT_REASONING_ENGINE_RESOURCE_NAME")
            if not self.summary_engine_resource_name:
                missing.append("VISUALSPRINT_SUMMARY_ENGINE_RESOURCE_NAME")
            if not self.action_engine_resource_name:
                missing.append("VISUALSPRINT_ACTION_ENGINE_RESOURCE_NAME")
            if not self.google_api_access_token and self.deployment_target != "cloud_run":
                missing.append(
                    "VISUALSPRINT_GOOGLE_API_ACCESS_TOKEN or Cloud Run service identity"
                )
        else:
            if not self.reasoning_agent_id:
                missing.append("VISUALSPRINT_REASONING_AGENT_ID")
            if not self.summary_agent_id:
                missing.append("VISUALSPRINT_SUMMARY_AGENT_ID")
            if not self.action_agent_id:
                missing.append("VISUALSPRINT_ACTION_AGENT_ID")
            if not self.reasoning_agent_endpoint_url:
                missing.append("VISUALSPRINT_REASONING_AGENT_ENDPOINT_URL")
            if not self.summary_agent_endpoint_url:
                missing.append("VISUALSPRINT_SUMMARY_AGENT_ENDPOINT_URL")
            if not self.action_agent_endpoint_url:
                missing.append("VISUALSPRINT_ACTION_AGENT_ENDPOINT_URL")
        if self.deployment_target == "cloud_run":
            if (
                self.agent_runtime_backend == "bridge"
                and not self.bridge_auth_configured
            ):
                missing.append(
                    "VISUALSPRINT_AGENT_BRIDGE_BEARER_TOKEN or "
                    "VISUALSPRINT_AGENT_BRIDGE_BEARER_TOKEN_SECRET_NAME"
                )
        return tuple(missing)

    @property
    def deployment_ready(self) -> bool:
        if self.deployment_target == "local_dev":
            return True
        return self.agent_mode == "configured_cloud" and not self.missing_cloud_configuration

    @property
    def health_note(self) -> str:
        if self.agent_mode == "mock":
            return (
                "The agents service is running in deterministic mock mode while the real "
                "Google Cloud Agent Builder adapter is still being wired."
            )
        if (
            self.agent_runtime_backend == "vertex_ai_reasoning_engine"
            and self.cloud_adapter_ready
        ):
            return (
                "Vertex AI Reasoning Engine runtime configuration is present. The service "
                "can call Agent Builder runtime query endpoints directly before falling back locally."
            )
        if self.deployment_target == "cloud_run" and self.deployment_ready:
            return (
                "Cloud Run deployment-facing configuration is present. The service is "
                "ready to attempt bridge-based agent invocations with secret-backed auth."
            )
        if self.cloud_adapter_ready:
            return (
                "Cloud adapter configuration and bridge endpoints are present. The service "
                "will try real agent invocations before falling back locally."
            )
        return (
            "Configured cloud mode was selected, but one or more agent ids or bridge "
            "endpoints are still missing. Local deterministic fallback remains active."
        )


def build_settings(environ: Mapping[str, str] | None = None) -> Settings:
    source = os.environ if environ is None else environ
    return Settings(
        environment=source.get("VISUALSPRINT_ENV", "development"),
        selected_track=source.get("VISUALSPRINT_TRACK", "elastic"),
        agent_mode=_resolve_agent_mode(source),
        deployment_target=_resolve_deployment_target(source),
        agent_runtime_backend=_resolve_agent_runtime_backend(source),
        google_cloud_project_id=_get(source, "VISUALSPRINT_GOOGLE_CLOUD_PROJECT_ID"),
        google_cloud_project_number=_get(source, "VISUALSPRINT_GOOGLE_CLOUD_PROJECT_NUMBER"),
        google_cloud_location=_get(source, "VISUALSPRINT_GOOGLE_CLOUD_LOCATION"),
        agent_application_id=_get(source, "VISUALSPRINT_AGENT_APPLICATION_ID"),
        reasoning_agent_id=_get(source, "VISUALSPRINT_REASONING_AGENT_ID"),
        summary_agent_id=_get(source, "VISUALSPRINT_SUMMARY_AGENT_ID"),
        action_agent_id=_get(source, "VISUALSPRINT_ACTION_AGENT_ID"),
        reasoning_engine_resource_name=_get_any(
            source,
            "VISUALSPRINT_REASONING_ENGINE_RESOURCE_NAME",
            "VISUALSPRINT_REASONING_AGENT_RESOURCE",
        ),
        summary_engine_resource_name=_get_any(
            source,
            "VISUALSPRINT_SUMMARY_ENGINE_RESOURCE_NAME",
            "VISUALSPRINT_SUMMARY_AGENT_RESOURCE",
        ),
        action_engine_resource_name=_get_any(
            source,
            "VISUALSPRINT_ACTION_ENGINE_RESOURCE_NAME",
            "VISUALSPRINT_ACTION_AGENT_RESOURCE",
        ),
        reasoning_agent_endpoint_url=_get(source, "VISUALSPRINT_REASONING_AGENT_ENDPOINT_URL"),
        summary_agent_endpoint_url=_get(source, "VISUALSPRINT_SUMMARY_AGENT_ENDPOINT_URL"),
        action_agent_endpoint_url=_get(source, "VISUALSPRINT_ACTION_AGENT_ENDPOINT_URL"),
        reasoning_query_url=_get(source, "VISUALSPRINT_REASONING_QUERY_URL"),
        summary_query_url=_get(source, "VISUALSPRINT_SUMMARY_QUERY_URL"),
        action_query_url=_get(source, "VISUALSPRINT_ACTION_QUERY_URL"),
        google_api_access_token=_get(source, "VISUALSPRINT_GOOGLE_API_ACCESS_TOKEN"),
        agent_bridge_bearer_token=_get(source, "VISUALSPRINT_AGENT_BRIDGE_BEARER_TOKEN"),
        agent_bridge_bearer_token_secret_name=_get(
            source,
            "VISUALSPRINT_AGENT_BRIDGE_BEARER_TOKEN_SECRET_NAME",
        ),
        agent_runtime_service_account=_get(source, "VISUALSPRINT_AGENT_RUNTIME_SERVICE_ACCOUNT"),
        agent_request_timeout_seconds=float(
            source.get("VISUALSPRINT_AGENT_REQUEST_TIMEOUT_SECONDS", "10.0")
        ),
        elastic_mcp_endpoint=_get_any(
            source,
            "VISUALSPRINT_MCP_ENDPOINT",
            "VISUALSPRINT_ELASTIC_MCP_ENDPOINT",
        ),
        elastic_api_key=_get(source, "VISUALSPRINT_ELASTIC_API_KEY"),
        elastic_api_key_secret_name=_get(source, "VISUALSPRINT_ELASTIC_API_KEY_SECRET_NAME"),
        service_account_email=_get(source, "VISUALSPRINT_SERVICE_ACCOUNT_EMAIL"),
        cloud_run_service_url=_get(source, "VISUALSPRINT_CLOUD_RUN_SERVICE_URL"),
        control_plane_url=_get(source, "VISUALSPRINT_CONTROL_PLANE_URL"),
        control_plane_bearer_token=_get(source, "VISUALSPRINT_CONTROL_PLANE_BEARER_TOKEN"),
        reasoning_model=_resolve_agent_model(source, "VISUALSPRINT_REASONING_MODEL"),
        summary_model=_resolve_agent_model(source, "VISUALSPRINT_SUMMARY_MODEL"),
        action_model=_resolve_agent_model(source, "VISUALSPRINT_ACTION_MODEL"),
        allowed_origins=_resolve_allowed_origins(source),
    )


settings = build_settings()
