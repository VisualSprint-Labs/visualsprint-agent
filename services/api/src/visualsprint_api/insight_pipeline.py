"""Deterministic chunk-insight assembler for future reasoning-agent inputs."""

from __future__ import annotations

from visualsprint_api.models import (
    ChunkContext,
    ChunkInsight,
    ChunkInsightFocus,
    MeetingDetail,
    MeetingStateSnapshot,
    ScreenEvent,
    SearchPriorOutcomesRequest,
    TranscriptSegment,
)


def build_chunk_insight(
    meeting: MeetingDetail,
    meeting_state: MeetingStateSnapshot,
    chunk_context: ChunkContext,
) -> ChunkInsight:
    """Assemble the agent-ready payload for one processed chunk."""

    transcript_segments = chunk_context.transcriptSegments
    screen_events = chunk_context.screenEvents
    latest_segment = transcript_segments[-1] if transcript_segments else None
    topic_label = _infer_topic_label(transcript_segments, screen_events)

    focus_areas = _build_focus_areas(topic_label, transcript_segments, screen_events)
    memory_queries = [
        SearchPriorOutcomesRequest(
            recordType=focus.recordType,
            summary=focus.summary,
            detail=focus.detail,
        )
        for focus in focus_areas[:3]
    ]

    attention_flags = [
        f"Chunk {chunk_context.chunk.sequence} is the latest recorded evidence window for this meeting.",
        (
            f"{len(meeting_state.openBlockers)} blockers and {len(meeting_state.openQuestions)} open questions "
            "are already active in the running state."
        ),
    ]
    if latest_segment is not None:
        attention_flags.append(
            f"{latest_segment.speakerLabel} closed the chunk, so their final statement is likely the strongest delta."
        )
    if any(event.kind in {"terminal", "error"} for event in screen_events):
        attention_flags.append(
            "Visible operational evidence is present, so blocker claims should cite the screen directly."
        )

    return ChunkInsight(
        meetingId=meeting.id,
        meetingTitle=meeting.title,
        meetingNotes=meeting.notes,
        clientChunkId=chunk_context.chunk.clientChunkId,
        focusSummary=(
            f"Chunk {chunk_context.chunk.sequence} centers on {topic_label}; "
            "the reasoning agent should decide what changed, what remains unresolved, "
            "and which historical outcomes are worth comparing."
        ),
        attentionFlags=attention_flags[:4],
        reasoningChecklist=[
            "Identify only durable decisions, commitments, blockers, or open questions.",
            "Anchor every claim in the transcript window or visible screen evidence.",
            "Check whether the candidate signal is already open in the running meeting state.",
            "Use memory lookup only for signals that appear durable enough to compare historically.",
        ],
        focusAreas=focus_areas,
        memoryQueries=memory_queries,
        transcriptSegments=[segment.model_copy(deep=True) for segment in transcript_segments],
        screenEvents=[screen_event.model_copy(deep=True) for screen_event in screen_events],
        meetingState=meeting_state,
        chunkContext=chunk_context,
    )


def _build_focus_areas(
    topic_label: str,
    transcript_segments: list[TranscriptSegment],
    screen_events: list[ScreenEvent],
) -> list[ChunkInsightFocus]:
    transcript_evidence = [
        f"{segment.speakerLabel}: {segment.text}" for segment in transcript_segments[:2]
    ]
    screen_evidence = [f"{event.kind}: {event.summary}" for event in screen_events[:2]]
    latest_statement = (
        transcript_segments[-1].text
        if transcript_segments
        else "The recorder has not yielded transcript evidence yet."
    )
    visual_summary = (
        screen_events[0].summary
        if screen_events
        else "No extracted screen evidence is available yet."
    )

    focus_areas = [
        ChunkInsightFocus(
            recordType="decision",
            summary=f"Decision pressure around {topic_label}",
            detail=(
                "The transcript suggests the team is converging on a concrete call. "
                f"Latest statement: {latest_statement}"
            ),
            evidence=(transcript_evidence + screen_evidence)[:4],
        )
    ]

    if any(event.kind in {"terminal", "error"} for event in screen_events):
        focus_areas.append(
            ChunkInsightFocus(
                recordType="blocker",
                summary=f"Operational blocker signs around {topic_label}",
                detail=(
                    "Visible screen evidence indicates an active technical obstacle that may need "
                    f"to remain open. Primary screen signal: {visual_summary}"
                ),
                evidence=(screen_evidence + transcript_evidence)[:4],
            )
        )

    if transcript_segments:
        focus_areas.append(
            ChunkInsightFocus(
                recordType="commitment",
                summary=f"Follow-up ownership implied by the {topic_label} discussion",
                detail=(
                    "The transcript window contains action-oriented language, so the reasoning step "
                    "should check whether someone accepted ownership or a due hint."
                ),
                evidence=transcript_evidence[:3],
            )
        )

    focus_areas.append(
        ChunkInsightFocus(
            recordType="open_question",
            summary=f"Remaining uncertainty after the {topic_label} exchange",
            detail=(
                "If the transcript or screen evidence leaves scope, owner, or timing unresolved, "
                "capture it as an open question instead of forcing a final decision."
            ),
            evidence=(transcript_evidence[-1:] + screen_evidence[:1])[:3],
        )
    )

    return focus_areas


def _infer_topic_label(
    transcript_segments: list[TranscriptSegment],
    screen_events: list[ScreenEvent],
) -> str:
    combined_text = " ".join(
        [segment.text.lower() for segment in transcript_segments]
        + [event.summary.lower() for event in screen_events]
    )

    if "auth" in combined_text or "release" in combined_text:
        return "release stability"
    if "migration" in combined_text or "staging" in combined_text:
        return "deployment validation"
    if "alert" in combined_text or "ownership" in combined_text:
        return "operational ownership"
    return "meeting follow-through"
