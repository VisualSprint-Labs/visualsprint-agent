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


def build_reasoning_agent_blueprint() -> AgentBlueprint:
    return AgentBlueprint(
        agent_id="visualsprint_reasoning_agent",
        display_name="VisualSprint Reasoning Agent",
        goal=(
            "Turn assembled chunk context into durable structured outputs while "
            "avoiding duplicate or weak signals."
        ),
        input_contract="ChunkInsight",
        output_contract="RegisterAgentOutputsRequest",
        instructions=(
            "Read every transcriptSegments entry and every screenEvents entry in the input before deciding whether a signal is durable.",
            "Screen evidence matters: if the visible screen shows code, terminals, errors, diagrams, or slides, anchor blockers and decisions to that visual evidence.",
            "Prefer updates, resolutions, or reopen events over duplicate net-new records when the running state already contains the issue.",
            "Use historical retrieval (search_prior_outcomes) before assigning recurring or reopened memory relations.",
            "Treat backend-injected memoryMatches as pre-searched historical context and only call search_prior_outcomes when you need additional comparison depth.",
            "Return schema-valid structured outputs only.",
            "Do not invent evidence that is not present in the supplied transcriptSegments or screenEvents.",
            "If the chunk contains no durable decision, commitment, blocker, or open question, return empty arrays.",
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
        enforce_output_schema=False,
        notes=(
            "Expose memory retrieval and output registration tools for ADK deploy wiring. "
            "The control plane may also pre-inject memoryMatches before reasoning runs.",
        ),
    )


def build_reasoning_root_agent() -> object:
    return create_root_agent(build_reasoning_agent_scaffold())


root_agent = build_reasoning_root_agent()
