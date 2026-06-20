"""Reasoning-agent blueprint aligned to the VisualSprint repo contracts."""

from __future__ import annotations

from visualsprint_agents.adk.prompting import render_instruction_text
from visualsprint_agents.adk.runtime import AdkAgentScaffold, create_root_agent
from visualsprint_agents.adk.shared import AgentBlueprint
from visualsprint_agents.adk.tool_contracts import (
    REGISTER_OUTPUTS_TOOL,
    SEARCH_PRIOR_OUTCOMES_TOOL,
)
from visualsprint_agents.adk.tools import register_outputs, search_prior_outcomes
from visualsprint_agents.config import settings
from visualsprint_agents.models import ChunkInsightRequest, ReasoningRunResponse


_REASONING_OUTPUT_SCHEMA = """\
Return a single JSON object — no markdown, no code fences, no explanation:
{
  "clientChunkId": "<value from input>",
  "decisions": [
    {"title": "one-line decision statement", "rationale": "why the team chose this", "speakerLabel": "who drove it"}
  ],
  "commitments": [
    {"ownerLabel": "person who owns it", "action": "what they will do", "dueHint": "when, e.g. end-of-sprint"}
  ],
  "blockers": [
    {"summary": "what is blocked", "severity": "low|medium|high", "ownerLabel": "owner or unknown"}
  ],
  "openQuestions": [
    {"question": "the unresolved question", "speakerLabel": "who raised it"}
  ],
  "memoryMatches": [],
  "resolvedDecisionIds": [],
  "resolvedCommitmentIds": [],
  "resolvedBlockerIds": [],
  "resolvedOpenQuestionIds": []
}
Omit array items for types with no evidence. Keep all nine keys present.\
"""


def build_reasoning_agent_blueprint() -> AgentBlueprint:
    return AgentBlueprint(
        agent_id="visualsprint_reasoning_agent",
        display_name="VisualSprint Reasoning Agent",
        goal=(
            "Extract durable decisions, commitments, blockers, and open questions "
            "from meeting chunk context and emit them as structured JSON."
        ),
        input_contract="ChunkInsight",
        output_contract="ReasoningRunResponse",
        instructions=(
            "The input JSON contains `focusSummary` (a plain-text digest of this chunk), "
            "`focusAreas` (pre-identified signals with recordType, summary, detail), "
            "and optionally `transcriptSegments` (timestamped speaker utterances). "
            "Use all three as your evidence base.",
            "Each `focusAreas` item is a confirmed signal: map it directly to the matching "
            "output array. `decision` → decisions[], `commitment` → commitments[], "
            "`blocker` → blockers[], `open_question` → openQuestions[].",
            "Also extract any additional clear decisions, commitments, blockers, or open "
            "questions you find in `transcriptSegments` that are not already covered by focusAreas.",
            "For `speakerLabel` and `ownerLabel`: use names from the transcript if present, "
            "otherwise use 'unknown'.",
            "Prefer updates or resolutions over duplicate new records when the running state "
            "already contains the issue.",
            "Only call `search_prior_outcomes` when you need historical depth beyond what "
            "memoryMatches already provide.",
            _REASONING_OUTPUT_SCHEMA,
        ),
        tools=(
            SEARCH_PRIOR_OUTCOMES_TOOL,
            REGISTER_OUTPUTS_TOOL,
        ),
    )


def build_reasoning_agent_scaffold() -> AdkAgentScaffold:
    blueprint = build_reasoning_agent_blueprint()
    return AdkAgentScaffold(
        agent_id=blueprint.agent_id,
        display_name=blueprint.display_name,
        description=(
            "Reason over assembled chunk context and emit durable structured outcomes "
            "for the VisualSprint control plane."
        ),
        model=settings.reasoning_model,
        instruction=render_instruction_text(
            blueprint,
            input_contract=blueprint.input_contract,
            output_contract=blueprint.output_contract,
            output_schema_enforced=True,
        ),
        input_model=ChunkInsightRequest,
        output_model=ReasoningRunResponse,
        input_schema=ChunkInsightRequest.model_json_schema(),
        output_schema=ReasoningRunResponse.model_json_schema(),
        tools=(search_prior_outcomes, register_outputs),
        output_key="reasoning_run_response",
        include_contents="none",
        enforce_output_schema=True,
        notes=(
            "Expose memory retrieval and output registration tools for ADK deploy wiring. "
            "The control plane may also pre-inject memoryMatches before reasoning runs.",
        ),
    )


def build_reasoning_root_agent() -> object:
    return create_root_agent(build_reasoning_agent_scaffold())


root_agent = build_reasoning_root_agent()
