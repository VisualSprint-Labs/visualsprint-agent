"""Action-agent blueprint aligned to the VisualSprint repo contracts."""

from __future__ import annotations

from visualsprint_agents.adk.prompting import render_instruction_text
from visualsprint_agents.adk.runtime import AdkAgentScaffold, create_root_agent
from visualsprint_agents.adk.shared import AgentBlueprint
from visualsprint_agents.adk.tool_contracts import CREATE_ACTION_RECOMMENDATIONS_TOOL
from visualsprint_agents.config import settings
from visualsprint_agents.models import ActionAgentRequest, ActionAgentResponse


_ACTION_OUTPUT_SCHEMA = """\
Return a single JSON object — no markdown, no code fences, no prose:
{
  "meetingId": "<value from input meetingId>",
  "recommendations": [
    {
      "type": "jira_create_issue | jira_update_issue | jira_resolve_issue | slack_post_summary | slack_broadcast_decision | slack_alert_blocker | slack_remind_commitment | slack_notify_resolution",
      "urgency": "critical | high | medium | low",
      "confidence": 0.0,
      "jiraDetails": {
        "action": "create_issue | update_issue | resolve_issue",
        "issueType": "task | story | bug",
        "title": "...",
        "description": "...",
        "priority": "lowest | low | medium | high | highest",
        "ownerLabel": "name or 'not mentioned'",
        "evidence": ["short quote from the report"],
        "confidence": 0.0
      },
      "slackDetails": null,
      "evidence": ["short quote from the report"]
    }
  ]
}
Set jiraDetails for jira_* types (slackDetails null) and slackDetails for slack_*
types (jiraDetails null). A slackDetails object is:
{"type": "post_summary | broadcast_decision | alert_blocker | remind_commitment | notify_resolution", "channel": "name or 'not specified'", "title": "...", "message": "...", "evidence": ["..."], "confidence": 0.0}\
"""


def build_action_agent_blueprint() -> AgentBlueprint:
    return AgentBlueprint(
        agent_id="visualsprint_action_agent",
        display_name="VisualSprint Action Agent",
        goal=(
            "Turn a final meeting report into structured, approval-based action "
            "recommendations for Jira and Slack without executing them directly."
        ),
        input_contract="ActionAgentRequest",
        output_contract="ActionAgentResponse",
        instructions=(
            "Produce a recommendation for every actionable signal in the report. A commitment "
            "with an owner is a jira_create_issue (task); a reported error or failing check is a "
            "jira_create_issue (bug); a high-severity blocker is also a slack_alert_blocker; "
            "significant decisions warrant slack_broadcast_decision; an ended meeting warrants "
            "slack_post_summary. Do not return an empty list when the report contains "
            "decisions, commitments, or blockers.",
            "Anchor every recommendation in the report — quote the relevant decision, commitment, "
            "or blocker in the evidence array. Do not fabricate signals that are not in the report.",
            "For Jira: Task for implementation commitments, Story for product features, Bug for "
            "errors, update_issue when an existing issue is referenced, resolve_issue only when "
            "completion is explicitly confirmed.",
            "Set ownerLabel only when explicitly mentioned; otherwise use 'not mentioned'.",
            "Rank urgency from severity, number of affected teams, and explicit deadlines.",
            "Assign confidence 0.0-1.0 from evidence strength.",
            _ACTION_OUTPUT_SCHEMA,
        ),
        tools=(CREATE_ACTION_RECOMMENDATIONS_TOOL,),
    )


def build_action_agent_scaffold() -> AdkAgentScaffold:
    blueprint = build_action_agent_blueprint()
    return AdkAgentScaffold(
        agent_id=blueprint.agent_id,
        display_name=blueprint.display_name,
        description=(
            "Turn a final meeting report into durable, approval-based Jira and Slack "
            "action recommendations for the VisualSprint control plane."
        ),
        model=settings.action_model,
        instruction=render_instruction_text(
            blueprint,
            input_contract=blueprint.input_contract,
            output_contract=blueprint.output_contract,
            output_schema_enforced=True,
        ),
        input_model=ActionAgentRequest,
        output_model=ActionAgentResponse,
        input_schema=ActionAgentRequest.model_json_schema(),
        output_schema=ActionAgentResponse.model_json_schema(),
        tools=(),
        output_key="action_recommendations_response",
        include_contents="none",
        enforce_output_schema=True,
        notes=(
            "Output schema is enforced via controlled generation so Gemini emits "
            "schema-valid ActionAgentResponse JSON directly. The no-op recommendation "
            "tool is intentionally omitted (persistence happens in the control plane).",
        ),
    )


def build_action_root_agent() -> object:
    return create_root_agent(build_action_agent_scaffold())


root_agent = build_action_root_agent()
