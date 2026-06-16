"""Demo seed data for consistent hackathon demo recordings."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from visualsprint_api.models import (
    ActionRecommendation,
    BlockerRecord,
    CommitmentRecord,
    DecisionRecord,
    EvidenceReference,
    FinalReport,
    JiraRecommendation,
    LiveEvent,
    MeetingDetail,
    MeetingMetrics,
    MemoryMatch,
    OpenQuestionRecord,
    ScreenEvent,
    SlackRecommendation,
    TranscriptSegment,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _evidence(note: str) -> EvidenceReference:
    return EvidenceReference(
        chunkId=f"chk_{uuid4().hex[:12]}",
        clientChunkId=f"chunk-{uuid4().hex[:8]}",
        tStartMs=0,
        tEndMs=4000,
        transcriptRef=f"trn_{uuid4().hex[:12]}",
        frameRef=None,
        note=note,
    )


def build_demo_meeting() -> MeetingDetail:
    now = _utc_now()
    started_at = now - timedelta(minutes=12)
    ended_at = now - timedelta(minutes=2)
    created_at = now - timedelta(minutes=15)

    return MeetingDetail(
        id=f"mtg_demo_{uuid4().hex[:8]}",
        title="Release readiness sync",
        participantCount=4,
        status="ended",
        sourceConnector="browser_live_capture",
        primaryTrack="elastic",
        createdAt=created_at,
        startedAt=started_at,
        endedAt=ended_at,
        notes="Focus on decisions, owners, blockers, and next steps.",
        metrics=MeetingMetrics(
            decisionsCount=2,
            commitmentsCount=2,
            blockersCount=1,
            memoryMatchesCount=1,
            openQuestionsCount=1,
            transcriptSegmentsCount=6,
            visualEventsCount=4,
            captureEventsCount=1,
            captureChunksCount=3,
            capturedBytes=4_200_000,
            actionRecommendationsCount=4,
        ),
        latestEvents=[
            LiveEvent(
                id=f"evt_{uuid4().hex[:12]}",
                kind="system",
                at=ended_at,
                title="Meeting ended",
                detail="The session ended and the final report was generated.",
            ),
            LiveEvent(
                id=f"evt_{uuid4().hex[:12]}",
                kind="capture",
                at=started_at,
                title="Browser capture started",
                detail="Audio and screen context began streaming to the ingest pipeline.",
            ),
        ],
        activeCaptureSession=None,
        recentCaptureChunks=[],
        recentTranscriptSegments=[
            TranscriptSegment(
                id=f"trn_{uuid4().hex[:12]}",
                speakerLabel="Jordan",
                startedAt=started_at + timedelta(minutes=1),
                endedAt=started_at + timedelta(minutes=1, seconds=4),
                text="We have a release risk around the authentication flow because the environment config is still drifting.",
            ),
            TranscriptSegment(
                id=f"trn_{uuid4().hex[:12]}",
                speakerLabel="Mina",
                startedAt=started_at + timedelta(minutes=2),
                endedAt=started_at + timedelta(minutes=2, seconds=5),
                text="Let's lock the release path today and record the owner so the blocker does not roll into another sprint.",
            ),
            TranscriptSegment(
                id=f"trn_{uuid4().hex[:12]}",
                speakerLabel="Avery",
                startedAt=started_at + timedelta(minutes=5),
                endedAt=started_at + timedelta(minutes=5, seconds=4),
                text="The shared screen confirms the deployment pipeline failed on the same migration validation step again.",
            ),
            TranscriptSegment(
                id=f"trn_{uuid4().hex[:12]}",
                speakerLabel="Theo",
                startedAt=started_at + timedelta(minutes=7),
                endedAt=started_at + timedelta(minutes=7, seconds=6),
                text="If we isolate the data fix and rerun staging today, we can unblock the release candidate before tomorrow.",
            ),
            TranscriptSegment(
                id=f"trn_{uuid4().hex[:12]}",
                speakerLabel="Jordan",
                startedAt=started_at + timedelta(minutes=9),
                endedAt=started_at + timedelta(minutes=9, seconds=4),
                text="Support escalations increased after the last rollout, so we need a visible decision on alert ownership.",
            ),
            TranscriptSegment(
                id=f"trn_{uuid4().hex[:12]}",
                speakerLabel="Mina",
                startedAt=started_at + timedelta(minutes=11),
                endedAt=started_at + timedelta(minutes=11, seconds=5),
                text="I want the meeting summary to call out the exact commitment and whether this was promised in earlier meetings.",
            ),
        ],
        recentScreenEvents=[
            ScreenEvent(
                id=f"scr_{uuid4().hex[:12]}",
                kind="code_editor",
                summary="Auth configuration values are open in the editor.",
                frameTimestampMs=1200,
                recordedAt=started_at + timedelta(minutes=1, seconds=1),
            ),
            ScreenEvent(
                id=f"scr_{uuid4().hex[:12]}",
                kind="error",
                summary="A release checklist warning is visible beside the auth workflow.",
                frameTimestampMs=2800,
                recordedAt=started_at + timedelta(minutes=2, seconds=2),
            ),
            ScreenEvent(
                id=f"scr_{uuid4().hex[:12]}",
                kind="terminal",
                summary="The terminal shows a migration validation failure in staging.",
                frameTimestampMs=5000,
                recordedAt=started_at + timedelta(minutes=5, seconds=2),
            ),
            ScreenEvent(
                id=f"scr_{uuid4().hex[:12]}",
                kind="diagram",
                summary="A handoff diagram is visible for alert routing ownership.",
                frameTimestampMs=8200,
                recordedAt=started_at + timedelta(minutes=9, seconds=2),
            ),
        ],
        recentDecisions=[
            DecisionRecord(
                id=f"dec_{uuid4().hex[:12]}",
                title="Freeze net-new feature work until auth pipeline is stable",
                rationale="The team agreed to pause net-new work until the auth and pipeline evidence looks stable.",
                speakerLabel="Mina",
                status="open",
                firstSeenChunkId="client-chunk-002",
                lastUpdatedChunkId="client-chunk-002",
                recordedAt=started_at + timedelta(minutes=2),
                evidence=[_evidence("Mina: 'Let's lock the release path today...'")],
            ),
            DecisionRecord(
                id=f"dec_{uuid4().hex[:12]}",
                title="Assign alert ownership to the on-call platform team",
                rationale="Support escalations increased after the last rollout; a single owner must be visible.",
                speakerLabel="Jordan",
                status="open",
                firstSeenChunkId="client-chunk-003",
                lastUpdatedChunkId="client-chunk-003",
                recordedAt=started_at + timedelta(minutes=9),
                evidence=[_evidence("Jordan: '...we need a visible decision on alert ownership.'")],
            ),
        ],
        recentCommitments=[
            CommitmentRecord(
                id=f"cmt_{uuid4().hex[:12]}",
                ownerLabel="Theo",
                action="Isolate the data fix and rerun staging validation today",
                dueHint="Today",
                status="open",
                firstSeenChunkId="client-chunk-003",
                lastUpdatedChunkId="client-chunk-003",
                recordedAt=started_at + timedelta(minutes=7),
                evidence=[_evidence("Theo: '...rerun staging today, we can unblock...'")],
            ),
            CommitmentRecord(
                id=f"cmt_{uuid4().hex[:12]}",
                ownerLabel="Mina",
                action="Publish the release-readiness handoff in the engineering channel",
                dueHint="Tomorrow",
                status="open",
                firstSeenChunkId="client-chunk-004",
                lastUpdatedChunkId="client-chunk-004",
                recordedAt=started_at + timedelta(minutes=11),
                evidence=[_evidence("Mina: '...call out the exact commitment...'")],
            ),
        ],
        recentBlockers=[
            BlockerRecord(
                id=f"blk_{uuid4().hex[:12]}",
                summary="Auth config drift is blocking the release candidate",
                severity="high",
                ownerLabel="Avery",
                status="open",
                firstSeenChunkId="client-chunk-001",
                lastUpdatedChunkId="client-chunk-003",
                recordedAt=started_at + timedelta(minutes=1),
                evidence=[_evidence("Screen: auth configuration values open in editor.")],
            ),
        ],
        recentMemoryMatches=[
            MemoryMatch(
                id=f"mem_{uuid4().hex[:12]}",
                sourceMeetingId="mtg_demo_prev_001",
                summary="Similar auth config drift appeared in last sprint's release sync",
                sourceMeetingTitle="Sprint 24 release sync",
                strength="recurring",
                relation="recurring",
                score=0.84,
                snippet="A prior meeting raised a similar auth risk and required an explicit owner follow-up.",
                recordedAt=started_at + timedelta(minutes=2),
            ),
        ],
        recentOpenQuestions=[
            OpenQuestionRecord(
                id=f"qst_{uuid4().hex[:12]}",
                question="Which team confirms the final readiness gate before this topic is closed?",
                speakerLabel="Mina",
                status="open",
                firstSeenChunkId="client-chunk-004",
                lastUpdatedChunkId="client-chunk-004",
                recordedAt=started_at + timedelta(minutes=11),
                evidence=[_evidence("Mina asked about final readiness gate ownership.")],
            ),
        ],
        recentActionRecommendations=[],
    )


def build_demo_final_report(meeting_id: str, recorded_at: datetime) -> FinalReport:
    return FinalReport(
        meetingId=meeting_id,
        generatedAt=recorded_at,
        executiveSummary=(
            "The team aligned on freezing net-new feature work until the auth pipeline is stable. "
            "Theo committed to isolating the data fix and rerunning staging validation today, while "
            "Avery owns the high-severity auth config drift blocker. A recurring memory match from "
            "the previous sprint reinforces the need for explicit ownership before closing the topic."
        ),
        summarySource="local_fallback",
    )


def build_demo_action_recommendations(meeting_id: str) -> list[ActionRecommendation]:
    now = _utc_now()

    def _jira(title: str, description: str, issue_type: str, urgency: str) -> ActionRecommendation:
        return ActionRecommendation(
            id=f"act_{uuid4().hex[:12]}",
            meetingId=meeting_id,
            type="jira_create_issue",
            status="pending",
            urgency=urgency,  # type: ignore[arg-type]
            confidence=0.88,
            jiraDetails=JiraRecommendation(
                action="create_issue",
                issueType=issue_type,  # type: ignore[arg-type]
                title=title,
                description=description,
                priority="high" if urgency in {"critical", "high"} else "medium",
                ownerLabel="Avery",
                evidence=[_evidence(f"Recommended from release readiness sync: {title}")],
                confidence=0.88,
            ),
            evidence=[_evidence(f"Recommended from release readiness sync: {title}")],
            createdAt=now,
            updatedAt=now,
        )

    def _slack(title: str, message: str, action_type: str, urgency: str) -> ActionRecommendation:
        slack_type = action_type.removeprefix("slack_")
        return ActionRecommendation(
            id=f"act_{uuid4().hex[:12]}",
            meetingId=meeting_id,
            type=action_type,  # type: ignore[arg-type]
            status="pending",
            urgency=urgency,  # type: ignore[arg-type]
            confidence=0.82,
            slackDetails=SlackRecommendation(
                type=slack_type,  # type: ignore[arg-type]
                channel="#engineering",
                title=title,
                message=message,
                evidence=[_evidence(f"Recommended from release readiness sync: {title}")],
                confidence=0.82,
            ),
            evidence=[_evidence(f"Recommended from release readiness sync: {title}")],
            createdAt=now,
            updatedAt=now,
        )

    return [
        _jira(
            "Auth config drift blocking release candidate",
            "High severity blocker identified during release readiness sync. Owner: Avery. "
            "Resolve config drift before unblocking the release candidate.",
            "bug",
            "critical",
        ),
        _jira(
            "Isolate data fix and rerun staging validation",
            "Theo committed to isolating the data fix and rerunning staging validation today.",
            "task",
            "high",
        ),
        _slack(
            "Release readiness decision: freeze feature work",
            "The team decided to freeze net-new feature work until the auth pipeline is stable. "
            "Theo is validating the data fix in staging today.",
            "slack_broadcast_decision",
            "medium",
        ),
        _slack(
            "Commitment reminder: publish release handoff",
            "Mina committed to publishing the release-readiness handoff in the engineering channel by tomorrow.",
            "slack_remind_commitment",
            "medium",
        ),
    ]
