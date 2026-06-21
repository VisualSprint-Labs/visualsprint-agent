"""Jira action executor for VisualSprint."""

from __future__ import annotations

import base64
import json
from urllib import error, request

from visualsprint_api.config import settings
from visualsprint_api.models import ActionRecommendation, JiraRecommendation


def execute_jira_action(recommendation: ActionRecommendation) -> tuple[bool, str]:
    """Execute a Jira action. Returns (success, detail)."""

    jira_details = recommendation.jiraDetails
    if jira_details is None:
        return False, "No Jira details found in recommendation."

    if not settings.jira_base_url or not settings.jira_api_token_secret:
        return _execute_jira_stub(jira_details)

    if jira_details.action == "create_issue":
        return _create_jira_issue(jira_details)
    if jira_details.action == "update_issue":
        return _update_jira_issue(jira_details)
    if jira_details.action == "resolve_issue":
        return _resolve_jira_issue(jira_details)

    return False, f"Unsupported Jira action: {jira_details.action}"


def _jira_auth_header() -> str:
    """Build Basic Auth header using email:api_token."""
    # Jira uses email as the username and API token as the password.
    # We use a placeholder email if none is configured; in production
    # you should set VISUALSPRINT_JIRA_EMAIL or similar.
    email = (getattr(settings, "jira_email", None) or "api@visualsprint.dev").strip()
    # Defensive strip: the stored secret can carry a trailing CR/newline which
    # silently corrupts the Basic-auth header and yields a confusing 401.
    token = (settings.jira_api_token_secret or "").strip()
    credentials = f"{email}:{token}"
    encoded = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
    return f"Basic {encoded}"


# Synonyms so issue-type resolution works regardless of the Jira site's language
# (e.g. a Spanish site exposes "Tarea"/"Historia"/"Error" instead of Task/Story/Bug).
_ISSUE_TYPE_SYNONYMS = {
    "task": ("task", "tarea", "tâche", "aufgabe", "tarefa"),
    "story": ("story", "historia", "história", "geschichte", "récit"),
    "bug": ("bug", "error", "fallo", "defecto", "erreur", "fehler"),
}


def _jira_get(path: str) -> tuple[bool, object]:
    base_url = settings.jira_base_url.rstrip("/")
    try:
        response = request.urlopen(
            request.Request(
                url=f"{base_url}{path}",
                headers={"Accept": "application/json", "Authorization": _jira_auth_header()},
                method="GET",
            ),
            timeout=10,
        )
        return True, json.loads(response.read().decode("utf-8"))
    except error.HTTPError as e:
        body = e.read().decode("utf-8") if hasattr(e, "read") else ""
        return False, f"{e.code}: {body}"
    except error.URLError as e:
        return False, str(e.reason)


def _resolve_project_issue_meta(
    project_key: str, desired_type: str
) -> tuple[str | None, bool]:
    """Resolve the project's real issue-type name and whether priority is settable.

    Returns (issuetype_name, priority_supported). issuetype_name is None when the
    project metadata could not be read, in which case the caller falls back to the
    raw mapping.
    """
    ok, meta = _jira_get(
        f"/rest/api/2/issue/createmeta?projectKeys={project_key}"
        "&expand=projects.issuetypes.fields"
    )
    if not ok or not isinstance(meta, dict):
        return None, True
    projects = meta.get("projects") or []
    if not projects:
        return None, True
    issuetypes = projects[0].get("issuetypes") or []
    standard = [it for it in issuetypes if not it.get("subtask")]
    if not standard:
        return None, True

    wanted = _ISSUE_TYPE_SYNONYMS.get(desired_type, (desired_type,))
    chosen = None
    for it in standard:
        name = (it.get("name") or "").lower()
        if any(syn in name for syn in wanted):
            chosen = it
            break
    if chosen is None:
        # Prefer a generic task-like type, else the first standard type.
        chosen = next(
            (it for it in standard if "epic" not in (it.get("name") or "").lower()),
            standard[0],
        )
    priority_supported = "priority" in (chosen.get("fields") or {})
    return chosen.get("name"), priority_supported


def _create_jira_issue(jira_details: JiraRecommendation) -> tuple[bool, str]:
    base_url = settings.jira_base_url.rstrip("/")
    url = f"{base_url}/rest/api/2/issue"
    project_key = _resolve_project_key()

    issue_type_mapping = {"task": "Task", "story": "Story", "bug": "Bug"}
    priority_mapping = {
        "lowest": "Lowest",
        "low": "Low",
        "medium": "Medium",
        "high": "High",
        "highest": "Highest",
    }

    # Resolve the issue type (and priority support) against the project's real
    # schema so this works on non-English sites and odd project configs.
    resolved_type, priority_supported = _resolve_project_issue_meta(
        project_key, jira_details.issueType
    )
    jira_issue_type = resolved_type or issue_type_mapping.get(jira_details.issueType, "Task")

    fields: dict = {
        "project": {"key": project_key},
        "summary": jira_details.title,
        "description": jira_details.description,
        "issuetype": {"name": jira_issue_type},
    }
    if priority_supported:
        fields["priority"] = {"name": priority_mapping.get(jira_details.priority, "Medium")}

    headers = {
        "Content-Type": "application/json",
        "Authorization": _jira_auth_header(),
    }

    try:
        response = request.urlopen(
            request.Request(
                url=url,
                data=json.dumps({"fields": fields}).encode("utf-8"),
                headers=headers,
                method="POST",
            ),
            timeout=10,
        )
        result = json.loads(response.read().decode("utf-8"))
        issue_key = result.get("key", "unknown")
        return True, f"Jira issue created: {issue_key} ({jira_issue_type} in {project_key})"
    except error.HTTPError as e:
        body = e.read().decode("utf-8") if hasattr(e, "read") else ""
        return False, f"Jira API error {e.code}: {body}"
    except error.URLError as e:
        return False, f"Jira connection error: {e.reason}"


def _update_jira_issue(jira_details: JiraRecommendation) -> tuple[bool, str]:
    # Placeholder: requires issue key in jira_details.description or title
    return False, "Jira update not yet implemented."


def _resolve_jira_issue(jira_details: JiraRecommendation) -> tuple[bool, str]:
    # Placeholder: requires issue key
    return False, "Jira resolve not yet implemented."


def _resolve_project_key() -> str:
    """Resolve Jira project key from settings or fallback."""
    project_key = getattr(settings, "jira_project_key", None)
    if project_key:
        return project_key
    # Fallback to the confirmed project from testing
    return "SCRUM"


def _execute_jira_stub(jira_details: JiraRecommendation) -> tuple[bool, str]:
    action_label = jira_details.action.replace("_", " ").title()
    detail = (
        f"[JIRA STUB] {action_label}: '{jira_details.title}' "
        f"(type={jira_details.issueType}, priority={jira_details.priority}, "
        f"owner={jira_details.ownerLabel})"
    )
    return True, detail
