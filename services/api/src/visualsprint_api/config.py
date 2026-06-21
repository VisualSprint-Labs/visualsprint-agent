"""Configuration helpers for the VisualSprint API."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from typing import Mapping


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _get(environ: Mapping[str, str], key: str) -> str | None:
    value = environ.get(key)
    return value.strip() if value and value.strip() else None


def _get_any(environ: Mapping[str, str], *keys: str) -> str | None:
    for key in keys:
        value = _get(environ, key)
        if value is not None:
            return value
    return None


@dataclass(frozen=True)
class Settings:
    service_name: str = "visualsprint-api"
    environment: str = "development"
    version: str = "0.1.0"
    selected_track: str = "elastic"
    agents_service_url: str | None = None
    ingest_service_url: str | None = None
    media_service_url: str | None = None
    elasticsearch_url: str | None = None
    elasticsearch_api_key_secret: str | None = None
    elastic_index_outcomes: str | None = None
    elastic_mcp_server_url: str | None = None
    jira_base_url: str | None = None
    jira_api_token_secret: str | None = None
    jira_email: str | None = None
    jira_project_key: str | None = None
    slack_bot_token_secret: str | None = None
    slack_default_channel: str | None = None
    service_request_timeout_seconds: float = 0.5
    google_cloud_project: str | None = None
    google_cloud_location: str = "us-central1"
    vision_model: str = "gemini-2.5-flash"
    media_vision_timeout_seconds: float = 30.0
    supported_tracks: tuple[str, ...] = (
        "arize",
        "elastic",
        "fivetran",
        "gitlab",
        "mongodb",
        "dynatrace",
    )
    allowed_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    )

    @property
    def media_vision_configured(self) -> bool:
        """True when a real Gemini multimodal call can replace the screen/transcript stubs."""
        return self.google_cloud_project is not None

    @property
    def elasticsearch_url_configured(self) -> bool:
        return self.elasticsearch_url is not None

    @property
    def elasticsearch_api_key_configured(self) -> bool:
        return self.elasticsearch_api_key_secret is not None

    @property
    def elastic_mcp_server_configured(self) -> bool:
        return self.elastic_mcp_server_url is not None

    @property
    def elastic_writeback_configured(self) -> bool:
        return bool(
            self.elasticsearch_url
            and self.elasticsearch_api_key_secret
            and self.elastic_index_outcomes
        )

    @property
    def elastic_integration_note(self) -> str:
        if self.elastic_writeback_configured and self.elastic_mcp_server_configured:
            return (
                "Elastic write-back and MCP endpoint configuration are present. The next "
                "slice can replace in-memory memory stubs with real Elastic integrations."
            )
        if self.elastic_writeback_configured:
            return (
                "Elastic write-back configuration is present, but MCP connectivity is not "
                "configured yet. Historical retrieval still falls back locally."
            )
        return (
            "Elastic is still running in planning mode. Outcome indexing and MCP-backed "
            "historical retrieval are not configured yet."
        )


def build_settings(environ: Mapping[str, str] | None = None) -> Settings:
    source = os.environ if environ is None else environ
    return Settings(
        environment=source.get("VISUALSPRINT_ENV", "development"),
        selected_track=source.get("VISUALSPRINT_TRACK", "elastic"),
        agents_service_url=_get(source, "VISUALSPRINT_AGENTS_SERVICE_URL"),
        ingest_service_url=_get(source, "VISUALSPRINT_INGEST_SERVICE_URL"),
        media_service_url=_get(source, "VISUALSPRINT_MEDIA_SERVICE_URL"),
        elasticsearch_url=_get(source, "ELASTICSEARCH_URL"),
        elasticsearch_api_key_secret=_get_any(
            source,
            "ELASTICSEARCH_API_KEY_SECRET",
            "ELASTICSEARCH_API_KEY",
        ),
        elastic_index_outcomes=_get_any(
            source,
            "ELASTIC_INDEX_OUTCOMES",
            "ELASTICSEARCH_INDEX",
        ),
        elastic_mcp_server_url=_get(source, "ELASTIC_MCP_SERVER_URL"),
        jira_base_url=_get(source, "JIRA_BASE_URL"),
        jira_api_token_secret=_get(source, "JIRA_API_TOKEN_SECRET"),
        jira_email=_get(source, "JIRA_EMAIL"),
        jira_project_key=_get(source, "JIRA_PROJECT_KEY"),
        slack_bot_token_secret=_get(source, "SLACK_BOT_TOKEN_SECRET"),
        slack_default_channel=_get(source, "SLACK_DEFAULT_CHANNEL"),
        service_request_timeout_seconds=float(
            source.get("VISUALSPRINT_SERVICE_TIMEOUT_SECONDS", "0.5")
        ),
        google_cloud_project=_get_any(
            source,
            "VISUALSPRINT_GOOGLE_CLOUD_PROJECT_ID",
            "GOOGLE_CLOUD_PROJECT",
            "PROJECT_ID",
        ),
        google_cloud_location=source.get(
            "VISUALSPRINT_GOOGLE_CLOUD_LOCATION", "us-central1"
        ).strip()
        or "us-central1",
        vision_model=source.get("VISUALSPRINT_VISION_MODEL", "gemini-2.5-flash").strip()
        or "gemini-2.5-flash",
        media_vision_timeout_seconds=float(
            source.get("VISUALSPRINT_MEDIA_VISION_TIMEOUT_SECONDS", "30.0")
        ),
        allowed_origins=tuple(
            _split_csv(source.get("VISUALSPRINT_ALLOWED_ORIGINS"))
            or [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ]
        ),
    )


settings = build_settings()
