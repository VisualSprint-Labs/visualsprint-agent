"""Summary-agent blueprint aligned to the VisualSprint repo contracts."""

from __future__ import annotations

from visualsprint_agents.adk.prompting import render_instruction_text
from visualsprint_agents.adk.runtime import AdkAgentScaffold, create_root_agent
from visualsprint_agents.adk.shared import AgentBlueprint
from visualsprint_agents.adk.tool_contracts import FINALIZE_REPORT_TOOL
from visualsprint_agents.adk.tools import finalize_report
from visualsprint_agents.config import settings
from visualsprint_agents.models import FinalReportDraft, SummaryPacketRequest


_SUMMARY_OUTPUT_SCHEMA = """\
Return a single JSON object — no markdown, no code fences, no prose:
{
  "meetingId": "<value from input meetingId>",
  "generatedAt": "<current time as ISO-8601, e.g. 2026-06-20T10:00:00Z>",
  "executiveSummary": "<2-4 sentence narrative of what the meeting decided, who committed to what, and which risks remain open — write this yourself, do NOT copy draftExecutiveSummary verbatim>",
  "decisions": [{"title": "...", "rationale": "...", "speakerLabel": "...", "status": "open|updated|resolved|reopened"}],
  "commitments": [{"ownerLabel": "...", "action": "...", "dueHint": "...", "status": "open|updated|resolved|reopened"}],
  "blockers": [{"summary": "...", "severity": "low|medium|high", "ownerLabel": "...", "status": "open|updated|resolved|reopened"}],
  "openQuestions": [{"question": "...", "speakerLabel": "...", "status": "open|updated|resolved|reopened"}],
  "memoryHighlights": [{"summary": "...", "relation": "new|recurring|reopened|resolved_previously", "score": 0.0}]
}
Copy the decisions, commitments, blockers, and openQuestions arrays through from the
input packet (preserving each record's status). The executiveSummary is the field you
must actually author. Keep all keys present.\
"""


def build_summary_agent_blueprint() -> AgentBlueprint:
    return AgentBlueprint(
        agent_id="visualsprint_summary_agent",
        display_name="VisualSprint Summary Agent",
        goal=(
            "Turn the assembled meeting summary packet into a final structured "
            "report that preserves durable outcomes and unresolved risks."
        ),
        input_contract="MeetingSummaryPacket",
        output_contract="FinalReportDraft",
        instructions=(
            "Write a real executiveSummary: a concise narrative of durable outcomes, "
            "not a replay of the full discussion and not a copy of draftExecutiveSummary.",
            "Keep commitments explicit with owners and due hints when present.",
            "Preserve unresolved blockers and open questions instead of hiding them in prose.",
            "Carry the decisions, commitments, blockers, and openQuestions arrays through "
            "from the input packet, preserving each record's status field.",
            "Use historical memory only when it changes confidence, priority, or urgency.",
            _SUMMARY_OUTPUT_SCHEMA,
        ),
        tools=(FINALIZE_REPORT_TOOL,),
    )


def build_summary_agent_scaffold() -> AdkAgentScaffold:
    blueprint = build_summary_agent_blueprint()
    return AdkAgentScaffold(
        agent_id=blueprint.agent_id,
        display_name=blueprint.display_name,
        description=(
            "Turn the assembled meeting summary packet into a durable final report for "
            "the VisualSprint control plane."
        ),
        model=settings.summary_model,
        instruction=render_instruction_text(
            blueprint,
            input_contract=blueprint.input_contract,
            output_contract=blueprint.output_contract,
            output_schema_enforced=True,
        ),
        input_model=SummaryPacketRequest,
        output_model=FinalReportDraft,
        input_schema=SummaryPacketRequest.model_json_schema(),
        output_schema=FinalReportDraft.model_json_schema(),
        tools=(finalize_report,),
        output_key="final_report_draft",
        include_contents="none",
        enforce_output_schema=True,
        notes=(
            "Expose finalize_report for ADK deploy wiring while the control plane "
            "continues to own deterministic persistence.",
        ),
    )


def build_summary_root_agent() -> object:
    return create_root_agent(build_summary_agent_scaffold())


root_agent = build_summary_root_agent()
