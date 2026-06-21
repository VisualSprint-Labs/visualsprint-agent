"""In-memory repository for local VisualSprint development."""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Callable
from uuid import uuid4

from visualsprint_api.config import settings
from visualsprint_api.vision_pipeline import analyze_chunk_media
from visualsprint_api.elastic_client import (
    search_prior_outcomes_in_elasticsearch,
    upsert_indexed_outcomes_to_elasticsearch,
)
from visualsprint_api.insight_pipeline import build_chunk_insight
from visualsprint_api.action_executors import execute_jira_action, execute_slack_action
from visualsprint_api.models import (
    ActionApprovalRequest,
    ActionRecommendation,
    ActionRecommendationInput,
    ActionRecommendationStatus,
    ActionRecommendationType,
    ActionExecutionResult,
    AgentBlockerInput,
    AgentCommitmentInput,
    AgentDecisionInput,
    AgentMemoryMatchInput,
    AgentOpenQuestionInput,
    BlockerRecord,
    CaptureChunkSummary,
    CaptureChunkUploadTarget,
    CaptureSessionSummary,
    ChunkContext,
    ChunkInsight,
    CompleteCaptureChunkUploadRequest,
    ProcessingSourceMode,
    CommitmentRecord,
    CreateMeetingRequest,
    DecisionRecord,
    EvidenceReference,
    FinalReport,
    IndexedOutcomeDocument,
    JiraRecommendation,
    MeetingStateSnapshot,
    MeetingSummaryPacket,
    OpenQuestionRecord,
    RegisterCaptureChunkRequest,
    RegisterAgentOutputsRequest,
    SearchPriorOutcomesRequest,
    SlackRecommendation,
    StartCaptureSessionRequest,
    LiveEvent,
    MemoryMatch,
    MeetingDetail,
    MeetingMetrics,
    MeetingSummary,
)
from visualsprint_api.service_clients import (
    process_media_chunk_with_source,
    process_transcript_chunk_with_source,
    reserve_chunk_upload_target,
    run_action_agent_with_source,
    run_chunk_reasoning_with_source,
    run_summary_agent_with_source,
)
from visualsprint_api.summary_pipeline import build_meeting_summary_packet


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MeetingInvariantError(ValueError):
    """Raised when a meeting or capture mutation violates lifecycle rules."""


def _normalize_recorder_mime_type(value: str | None) -> str:
    if value is None or not value.strip():
        return "browser-default"
    return value.strip()


DECISION_TEMPLATES = (
    (
        "Stabilize the release path before feature work resumes",
        "The team agreed to freeze net-new work until the auth and pipeline evidence looks stable.",
    ),
    (
        "Separate the migration fix from the wider deployment batch",
        "Keeping the rollback surface smaller reduces release risk and shortens validation time.",
    ),
    (
        "Promote alert ownership into the sprint handoff checklist",
        "The group wants recurring operational work to survive meeting boundaries instead of staying verbal only.",
    ),
)

COMMITMENT_TEMPLATES = (
    ("Jordan", "Publish the release checklist update in the engineering channel", "Today"),
    ("Mina", "Run the staging migration fix and attach screenshots to the ticket", "Before standup"),
    ("Theo", "Update the alert ownership document with the new on-call handoff", "This sprint"),
)

BLOCKER_TEMPLATES = (
    ("Auth configuration drift is still blocking the release candidate.", "high", "Avery"),
    ("Migration validation is failing on repeated staging runs.", "medium", "Mina"),
    ("Alert routing ownership is unclear across platform and support.", "medium", "Theo"),
)

MEMORY_TEMPLATES = (
    (
        "mtg_hist_auth_01",
        "A similar auth blocker was raised two weeks ago and was marked unresolved.",
        "Sprint 21 release review",
        "recurring",
        "recurring",
        0.93,
        "Auth configuration drift blocked the release candidate during sprint 21.",
    ),
    (
        "mtg_hist_migration_01",
        "The same migration issue appeared in a prior staging rehearsal and required a scoped rerun.",
        "Infra readiness sync",
        "related",
        "resolved_previously",
        0.82,
        "Migration validation failed during staging and was fixed with a scoped rerun.",
    ),
    (
        "mtg_hist_alerts_01",
        "Alert ownership drift was previously discussed during the last incident follow-up.",
        "Post-incident action review",
        "critical",
        "reopened",
        0.89,
        "Ownership ambiguity resurfaced after the prior incident review closed.",
    ),
)

OPEN_QUESTION_TEMPLATES = (
    "Should the release freeze be lifted immediately after the auth configuration fix is validated?",
    "Do we need a separate owner for rollback verification before the next deployment attempt?",
    "Which team should own the alert-routing handoff once this sprint closes?",
)


@dataclass(slots=True)
class MeetingStore:
    """Thread-safe in-memory meeting store for early development."""

    _meetings: dict[str, MeetingDetail] = field(default_factory=dict)
    _chunks_by_client_id: dict[tuple[str, str], CaptureChunkSummary] = field(
        default_factory=dict
    )
    _chunk_context_by_client_id: dict[tuple[str, str], ChunkContext] = field(
        default_factory=dict
    )
    _chunk_media_by_client_id: dict[tuple[str, str], tuple[bytes, str | None]] = field(
        default_factory=dict
    )
    _meeting_revisions: dict[str, int] = field(default_factory=dict)
    _final_reports: dict[str, FinalReport] = field(default_factory=dict)
    _indexed_outcomes: dict[tuple[str, str], IndexedOutcomeDocument] = field(default_factory=dict)
    _action_recommendations: dict[tuple[str, str], ActionRecommendation] = field(
        default_factory=dict
    )
    _lock: Lock = field(default_factory=Lock)

    def reset(self) -> None:
        """Clear all in-memory state for deterministic test setup."""

        with self._lock:
            self._meetings.clear()
            self._chunks_by_client_id.clear()
            self._chunk_context_by_client_id.clear()
            self._chunk_media_by_client_id.clear()
            self._meeting_revisions.clear()
            self._final_reports.clear()
            self._indexed_outcomes.clear()
            self._action_recommendations.clear()

    def list_meetings(self) -> list[MeetingSummary]:
        with self._lock:
            meetings = sorted(
                self._meetings.values(),
                key=lambda meeting: meeting.createdAt,
                reverse=True,
            )
            return [MeetingSummary.model_validate(meeting.model_dump()) for meeting in meetings]

    def create_meeting(self, payload: CreateMeetingRequest) -> MeetingDetail:
        created_at = _utc_now()
        meeting_id = f"mtg_{uuid4().hex[:12]}"
        detail = MeetingDetail(
            id=meeting_id,
            title=payload.title.strip(),
            participantCount=payload.participantCount,
            status="draft",
            sourceConnector=payload.sourceConnector,
            primaryTrack=settings.selected_track,
            createdAt=created_at,
            startedAt=None,
            endedAt=None,
            notes=payload.notes.strip(),
            metrics=MeetingMetrics(),
            latestEvents=[
                LiveEvent(
                    id=f"evt_{uuid4().hex[:12]}",
                    kind="system",
                    at=created_at,
                    title="Meeting session created",
                    detail=(
                        "The deterministic control plane created the meeting shell "
                        "and reserved it for the selected connector."
                    ),
                )
            ],
            activeCaptureSession=None,
            recentCaptureChunks=[],
            recentTranscriptSegments=[],
            recentScreenEvents=[],
            recentDecisions=[],
            recentCommitments=[],
            recentBlockers=[],
            recentMemoryMatches=[],
            recentOpenQuestions=[],
            recentActionRecommendations=[],
        )

        with self._lock:
            self._meetings[meeting_id] = detail
            self._meeting_revisions[meeting_id] = 0

        return detail

    def get_meeting(self, meeting_id: str) -> MeetingDetail | None:
        with self._lock:
            meeting = self._meetings.get(meeting_id)
            return None if meeting is None else meeting.model_copy(deep=True)

    def get_meeting_revision(self, meeting_id: str) -> int | None:
        with self._lock:
            if meeting_id not in self._meetings:
                return None
            return self._meeting_revisions.get(meeting_id, 0)

    def get_final_report(self, meeting_id: str) -> FinalReport | None:
        with self._lock:
            report = self._final_reports.get(meeting_id)
            return None if report is None else report.model_copy(deep=True)

    def get_summary_packet(self, meeting_id: str) -> MeetingSummaryPacket | None:
        with self._lock:
            meeting = self._meetings.get(meeting_id)
            if meeting is None:
                return None
            return build_meeting_summary_packet(
                meeting=meeting.model_copy(deep=True),
                meeting_state=self._build_meeting_state(meeting),
            )

    def list_indexed_outcomes(self, meeting_id: str) -> list[IndexedOutcomeDocument] | None:
        with self._lock:
            if meeting_id not in self._meetings:
                return None
            documents = [
                document.model_copy(deep=True)
                for (document_meeting_id, _), document in self._indexed_outcomes.items()
                if document_meeting_id == meeting_id
            ]
            documents.sort(key=lambda document: document.updatedAt, reverse=True)
            return documents

    def start_meeting(self, meeting_id: str) -> MeetingDetail | None:
        with self._lock:
            meeting = self._meetings.get(meeting_id)
            if meeting is None:
                return None
            if meeting.status == "draft":
                started_at = _utc_now()
                meeting.status = "live"
                meeting.startedAt = started_at
                meeting.metrics.captureEventsCount += 1
                meeting.latestEvents.insert(
                    0,
                    LiveEvent(
                        id=f"evt_{uuid4().hex[:12]}",
                        kind="capture",
                        at=started_at,
                        title="Live capture session started",
                        detail=(
                            "The meeting is now ready for browser-based capture intake "
                            "and chunk registration."
                        ),
                    ),
                )
                self._mark_meeting_updated(meeting.id)
            return meeting.model_copy(deep=True)

    def finalize_report(self, meeting_id: str) -> FinalReport | None:
        meeting_copy: MeetingDetail | None = None
        documents_to_sync: list[IndexedOutcomeDocument] = []
        with self._lock:
            meeting = self._meetings.get(meeting_id)
            if meeting is None:
                return None
            summary_packet = build_meeting_summary_packet(
                meeting=meeting.model_copy(deep=True),
                meeting_state=self._build_meeting_state(meeting),
            )
            report, summary_source = run_summary_agent_with_source(summary_packet)
            if report is None:
                report = self._build_final_report(meeting)
            report.summarySource = summary_source
            self._final_reports[meeting_id] = report
            self._mark_meeting_updated(meeting_id)
            meeting_copy = meeting.model_copy(deep=True)
            documents_to_sync = self._copy_indexed_outcomes_for_meeting(meeting_id)
            report_copy = report.model_copy(deep=True)

        self._sync_indexed_outcomes_to_elastic(meeting_copy, documents_to_sync)
        self.generate_action_recommendations(meeting_id)
        return report_copy

    def get_meeting_state(self, meeting_id: str) -> MeetingStateSnapshot | None:
        with self._lock:
            meeting = self._meetings.get(meeting_id)
            if meeting is None:
                return None
            return self._build_meeting_state(meeting)

    def get_chunk_context(
        self,
        meeting_id: str,
        client_chunk_id: str,
    ) -> ChunkContext | None:
        with self._lock:
            if meeting_id not in self._meetings:
                return None
            chunk_context = self._chunk_context_by_client_id.get((meeting_id, client_chunk_id))
            return None if chunk_context is None else chunk_context.model_copy(deep=True)

    def get_chunk_insight(
        self,
        meeting_id: str,
        client_chunk_id: str,
    ) -> ChunkInsight | None:
        meeting_copy: MeetingDetail | None = None
        chunk_context_copy: ChunkContext | None = None
        meeting_state: MeetingStateSnapshot | None = None
        with self._lock:
            meeting = self._meetings.get(meeting_id)
            if meeting is None:
                return None

            chunk_context = self._chunk_context_by_client_id.get((meeting_id, client_chunk_id))
            if chunk_context is None:
                return None

            meeting_copy = meeting.model_copy(deep=True)
            chunk_context_copy = chunk_context.model_copy(deep=True)
            meeting_state = self._build_meeting_state(meeting)

        insight = build_chunk_insight(
            meeting=meeting_copy,
            meeting_state=meeting_state,
            chunk_context=chunk_context_copy,
        )
        memory_matches = self._resolve_chunk_memory_matches(
            meeting_id=meeting_id,
            memory_queries=insight.memoryQueries,
        )
        if memory_matches:
            return insight.model_copy(update={"memoryMatches": memory_matches})
        return insight

    def search_prior_outcomes(
        self,
        meeting_id: str,
        payload: SearchPriorOutcomesRequest,
    ) -> list[MemoryMatch] | None:
        with self._lock:
            meeting = self._meetings.get(meeting_id)
            if meeting is None:
                return None
            meeting_copy = meeting.model_copy(deep=True)

        elastic_matches = search_prior_outcomes_in_elasticsearch(
            config=settings,
            meeting=meeting_copy,
            payload=payload,
        )
        if elastic_matches is not None:
            if len(elastic_matches) > 0:
                return [match.model_copy(deep=True) for match in elastic_matches[:3]]
            return [self._build_empty_memory_match(meeting_copy)]

        normalized_text = f"{payload.summary} {payload.detail}".lower()
        matches: list[MemoryMatch] = []

        for (
            source_meeting_id,
            summary,
            source_meeting_title,
            strength,
            relation,
            score,
            snippet,
        ) in MEMORY_TEMPLATES:
            keywords = _keywords_for_memory_template(source_meeting_id)
            if any(keyword in normalized_text for keyword in keywords):
                matches.append(
                    MemoryMatch(
                        id=f"mem_{uuid4().hex[:12]}",
                        sourceMeetingId=source_meeting_id,
                        summary=summary,
                        sourceMeetingTitle=source_meeting_title,
                        strength=strength,
                        relation=relation,
                        score=score,
                        snippet=snippet,
                        recordedAt=_utc_now(),
                    )
                )

        if len(matches) == 0:
            matches.append(self._build_empty_memory_match(meeting_copy))

        return [match.model_copy(deep=True) for match in matches[:3]]

    def register_outputs(
        self,
        meeting_id: str,
        payload: RegisterAgentOutputsRequest,
    ) -> tuple[MeetingDetail, MeetingStateSnapshot] | None:
        meeting_copy: MeetingDetail | None = None
        meeting_state: MeetingStateSnapshot | None = None
        documents_to_sync: list[IndexedOutcomeDocument] = []
        with self._lock:
            meeting = self._meetings.get(meeting_id)
            if meeting is None:
                return None

            chunk_context = self._chunk_context_by_client_id.get((meeting_id, payload.clientChunkId))
            if chunk_context is None:
                raise MeetingInvariantError("Chunk context was not found for output registration")

            recorded_at = chunk_context.chunk.recordedAt
            source_chunk = chunk_context.chunk
            evidence_refs = self._build_evidence_references(
                source_chunk,
                chunk_context.transcriptSegments,
                chunk_context.screenEvents,
            )

            self._persist_decisions(
                meeting,
                payload.decisions,
                recorded_at,
                source_chunk.clientChunkId,
                evidence_refs,
            )
            self._persist_commitments(
                meeting,
                payload.commitments,
                recorded_at,
                source_chunk.clientChunkId,
                evidence_refs,
            )
            self._persist_blockers(
                meeting,
                payload.blockers,
                recorded_at,
                source_chunk.clientChunkId,
                evidence_refs,
            )
            self._persist_open_questions(
                meeting,
                payload.openQuestions,
                recorded_at,
                source_chunk.clientChunkId,
                evidence_refs,
            )
            resolved_count = 0
            resolved_count += self._resolve_decisions(
                meeting,
                payload.resolvedDecisionIds,
                recorded_at,
                source_chunk.clientChunkId,
                evidence_refs,
            )
            resolved_count += self._resolve_commitments(
                meeting,
                payload.resolvedCommitmentIds,
                recorded_at,
                source_chunk.clientChunkId,
                evidence_refs,
            )
            resolved_count += self._resolve_blockers(
                meeting,
                payload.resolvedBlockerIds,
                recorded_at,
                source_chunk.clientChunkId,
                evidence_refs,
            )
            resolved_count += self._resolve_open_questions(
                meeting,
                payload.resolvedOpenQuestionIds,
                recorded_at,
                source_chunk.clientChunkId,
                evidence_refs,
            )
            self._persist_memory_matches(meeting, payload.memoryMatches, recorded_at)

            source_chunk.signalCount += (
                len(payload.decisions)
                + len(payload.commitments)
                + len(payload.blockers)
                + len(payload.openQuestions)
                + len(payload.memoryMatches)
                + resolved_count
            )
            meeting.latestEvents.insert(
                0,
                LiveEvent(
                    id=f"evt_{uuid4().hex[:12]}",
                    kind="decision",
                    at=recorded_at,
                    title="Agent outputs registered",
                    detail=(
                        f"Persisted outputs for {payload.clientChunkId}: "
                        f"{len(payload.decisions)} decisions, "
                        f"{len(payload.commitments)} commitments, "
                        f"{len(payload.blockers)} blockers, "
                        f"{len(payload.openQuestions)} open questions, "
                        f"and {resolved_count} resolved records."
                    ),
                ),
            )
            meeting.latestEvents = meeting.latestEvents[:12]
            self._mark_meeting_updated(meeting_id)
            meeting_copy = meeting.model_copy(deep=True)
            meeting_state = self._build_meeting_state(meeting)
            documents_to_sync = self._copy_indexed_outcomes_for_meeting(meeting_id)

        self._sync_indexed_outcomes_to_elastic(meeting_copy, documents_to_sync)
        return meeting_copy, meeting_state

    def end_meeting(self, meeting_id: str) -> MeetingDetail | None:
        with self._lock:
            meeting = self._meetings.get(meeting_id)
            if meeting is None:
                return None
            if meeting.status != "ended":
                ended_at = _utc_now()
                if meeting.startedAt is None:
                    meeting.startedAt = ended_at
                if (
                    meeting.activeCaptureSession is not None
                    and meeting.activeCaptureSession.status == "recording"
                ):
                    meeting.activeCaptureSession.status = "completed"
                    meeting.activeCaptureSession.endedAt = ended_at
                meeting.status = "ended"
                meeting.endedAt = ended_at
                meeting.latestEvents.insert(
                    0,
                    LiveEvent(
                        id=f"evt_{uuid4().hex[:12]}",
                        kind="system",
                        at=ended_at,
                        title="Meeting finalized",
                        detail=(
                            "The meeting lifecycle is closed and ready for the future "
                            "summary-agent flow."
                        ),
                    ),
                )
                self._mark_meeting_updated(meeting.id)
            return meeting.model_copy(deep=True)

    def start_capture_session(
        self,
        meeting_id: str,
        payload: StartCaptureSessionRequest,
    ) -> tuple[MeetingDetail, CaptureSessionSummary] | None:
        with self._lock:
            meeting = self._meetings.get(meeting_id)
            if meeting is None:
                return None

            started_at = _utc_now()
            capture_session = CaptureSessionSummary(
                id=f"cap_{uuid4().hex[:12]}",
                status="recording",
                sourceConnector="browser_live_capture",
                recorderMimeType=_normalize_recorder_mime_type(payload.recorderMimeType),
                hasDisplayVideo=payload.hasDisplayVideo,
                hasDisplayAudio=payload.hasDisplayAudio,
                hasMicrophoneAudio=payload.hasMicrophoneAudio,
                startedAt=started_at,
                endedAt=None,
                chunkCount=0,
                totalBytes=0,
            )

            meeting.activeCaptureSession = capture_session
            meeting.metrics.captureEventsCount += 1
            meeting.latestEvents.insert(
                0,
                LiveEvent(
                    id=f"evt_{uuid4().hex[:12]}",
                    kind="capture",
                    at=started_at,
                    title="Browser capture session registered",
                    detail=(
                        "The control plane registered a live browser capture session "
                        "and is ready to receive chunk metadata."
                    ),
                ),
            )
            self._mark_meeting_updated(meeting.id)

            return meeting.model_copy(deep=True), capture_session.model_copy(deep=True)

    def register_capture_chunk(
        self,
        meeting_id: str,
        payload: RegisterCaptureChunkRequest,
    ) -> tuple[MeetingDetail, CaptureSessionSummary, CaptureChunkSummary] | None:
        with self._lock:
            meeting = self._meetings.get(meeting_id)
            if meeting is None or meeting.activeCaptureSession is None:
                return None
            if meeting.activeCaptureSession.status != "recording":
                raise MeetingInvariantError(
                    "Capture chunks can only be registered while the session is recording"
                )

            chunk_key = (meeting_id, payload.clientChunkId)
            existing_chunk = self._chunks_by_client_id.get(chunk_key)
            if existing_chunk is not None:
                return (
                    meeting.model_copy(deep=True),
                    meeting.activeCaptureSession.model_copy(deep=True),
                    existing_chunk.model_copy(deep=True),
                )

            if any(
                chunk.sequence == payload.sequence
                for chunk in meeting.recentCaptureChunks
                if chunk.clientChunkId != payload.clientChunkId
            ):
                raise MeetingInvariantError(
                    "Chunk sequence already exists for the active capture session"
                )

            recorded_at = _utc_now()
            upload_target = reserve_chunk_upload_target(
                meeting_id=meeting_id,
                capture_session_id=meeting.activeCaptureSession.id,
                client_chunk_id=payload.clientChunkId,
                sequence=payload.sequence,
                mime_type=payload.mimeType,
            )
            chunk = CaptureChunkSummary(
                id=f"chk_{uuid4().hex[:12]}",
                clientChunkId=payload.clientChunkId,
                sequence=payload.sequence,
                recordedAt=recorded_at,
                durationMs=payload.durationMs,
                byteSize=payload.byteSize,
                mimeType=payload.mimeType,
                lifecycleStatus="registered",
                uploadStatus="pending",
                storageObjectPath=upload_target.objectPath,
                uploadTarget=upload_target,
                processingStatus="registered",
                frameCount=0,
                transcriptSegmentCount=0,
                visualEventCount=0,
                signalCount=0,
                transcriptSource="local_fallback",
                mediaSource="local_fallback",
                reasoningSource="local_fallback",
            )
            self._chunks_by_client_id[chunk_key] = chunk
            self._chunk_context_by_client_id[chunk_key] = ChunkContext(
                chunk=chunk.model_copy(deep=True),
                transcriptSegments=[],
                screenEvents=[],
            )

            meeting.activeCaptureSession.chunkCount += 1
            meeting.activeCaptureSession.totalBytes += payload.byteSize
            meeting.metrics.captureChunksCount += 1
            meeting.metrics.capturedBytes += payload.byteSize
            meeting.recentCaptureChunks.insert(0, chunk)
            meeting.recentCaptureChunks = meeting.recentCaptureChunks[:8]
            meeting.latestEvents.insert(
                0,
                LiveEvent(
                    id=f"evt_{uuid4().hex[:12]}",
                    kind="capture",
                    at=recorded_at,
                    title=f"Chunk {payload.sequence} registered",
                    detail=(
                        f"Registered {payload.byteSize} bytes of capture data "
                        f"for {payload.durationMs} ms using client chunk id "
                        f"{payload.clientChunkId}."
                    ),
                ),
            )
            self._mark_chunk_upload_ready(meeting, chunk)
            meeting.latestEvents = meeting.latestEvents[:12]
            self._mark_meeting_updated(meeting.id)

            return (
                meeting.model_copy(deep=True),
                meeting.activeCaptureSession.model_copy(deep=True),
                chunk,
            )

    def _store_chunk_media(
        self,
        chunk_key: tuple[str, str],
        payload: CompleteCaptureChunkUploadRequest,
    ) -> None:
        """Decode and stash the uploaded chunk media for the vision pass."""

        if not payload.mediaBase64:
            return
        try:
            media_bytes = base64.b64decode(payload.mediaBase64, validate=False)
        except (ValueError, binascii.Error):
            return
        if media_bytes:
            self._chunk_media_by_client_id[chunk_key] = (media_bytes, payload.mediaMimeType)

    def complete_capture_chunk_upload(
        self,
        meeting_id: str,
        payload: CompleteCaptureChunkUploadRequest,
    ) -> tuple[MeetingDetail, CaptureSessionSummary, CaptureChunkSummary] | None:
        with self._lock:
            meeting = self._meetings.get(meeting_id)
            if meeting is None or meeting.activeCaptureSession is None:
                return None
            if meeting.activeCaptureSession.status != "recording":
                raise MeetingInvariantError(
                    "Chunk upload completion requires an active recording capture session"
                )

            chunk_key = (meeting_id, payload.clientChunkId)
            chunk = self._chunks_by_client_id.get(chunk_key)
            if chunk is None:
                raise MeetingInvariantError("Chunk upload completion target was not found")
            if chunk.uploadStatus == "uploaded":
                return (
                    meeting.model_copy(deep=True),
                    meeting.activeCaptureSession.model_copy(deep=True),
                    chunk.model_copy(deep=True),
                )
            if chunk.uploadStatus != "ready":
                raise MeetingInvariantError(
                    "Chunk upload completion requires an upload-ready chunk"
                )

            self._store_chunk_media(chunk_key, payload)
            self._mark_chunk_uploaded(meeting, chunk)
            self._prepare_chunk_processing(meeting, chunk)
            meeting.latestEvents = meeting.latestEvents[:12]
            self._mark_meeting_updated(meeting.id)

            return (
                meeting.model_copy(deep=True),
                meeting.activeCaptureSession.model_copy(deep=True),
                chunk.model_copy(deep=True),
            )

    def run_chunk_reasoning(
        self,
        meeting_id: str,
        client_chunk_id: str,
    ) -> tuple[MeetingDetail, CaptureSessionSummary, CaptureChunkSummary] | None:
        with self._lock:
            meeting = self._meetings.get(meeting_id)
            if meeting is None or meeting.activeCaptureSession is None:
                return None

            chunk_key = (meeting_id, client_chunk_id)
            chunk = self._chunks_by_client_id.get(chunk_key)
            if chunk is None:
                raise MeetingInvariantError("Chunk reasoning target was not found")
            if chunk.processingStatus == "processed":
                return (
                    meeting.model_copy(deep=True),
                    meeting.activeCaptureSession.model_copy(deep=True),
                    chunk.model_copy(deep=True),
                )
            if chunk.uploadStatus != "uploaded":
                raise MeetingInvariantError(
                    "Chunk reasoning requires an uploaded chunk"
                )
            if chunk.processingStatus != "processing":
                raise MeetingInvariantError(
                    "Chunk reasoning requires assembled transcript and media context"
                )

            chunk_context = self._chunk_context_by_client_id.get(chunk_key)
            if chunk_context is None:
                raise MeetingInvariantError(
                    "Chunk reasoning requires assembled transcript and media context"
                )

            self._finalize_chunk_reasoning(meeting, chunk, chunk_context)
            meeting.latestEvents = meeting.latestEvents[:12]
            self._mark_meeting_updated(meeting.id)

            return (
                meeting.model_copy(deep=True),
                meeting.activeCaptureSession.model_copy(deep=True),
                chunk.model_copy(deep=True),
            )

    def complete_capture_session(
        self,
        meeting_id: str,
    ) -> tuple[MeetingDetail, CaptureSessionSummary] | None:
        with self._lock:
            meeting = self._meetings.get(meeting_id)
            if meeting is None or meeting.activeCaptureSession is None:
                return None

            completed_at = _utc_now()
            meeting.activeCaptureSession.status = "completed"
            meeting.activeCaptureSession.endedAt = completed_at
            meeting.latestEvents.insert(
                0,
                LiveEvent(
                    id=f"evt_{uuid4().hex[:12]}",
                    kind="capture",
                    at=completed_at,
                    title="Browser capture session completed",
                    detail=(
                        "The recorder stopped and the control plane closed the "
                        "capture session cleanly."
                    ),
                ),
            )
            self._mark_meeting_updated(meeting.id)

            return meeting.model_copy(deep=True), meeting.activeCaptureSession.model_copy(
                deep=True
            )

    def _mark_chunk_upload_ready(
        self,
        meeting: MeetingDetail,
        chunk: CaptureChunkSummary,
    ) -> None:
        recorded_at = chunk.recordedAt
        chunk.lifecycleStatus = "upload_ready"
        chunk.uploadStatus = "ready"
        meeting.latestEvents.insert(
            0,
            LiveEvent(
                id=f"evt_{uuid4().hex[:12]}",
                kind="capture",
                at=recorded_at,
                title=f"Chunk {chunk.sequence} upload contract prepared",
                detail=(
                    f"Storage key {chunk.storageObjectPath} is reserved for the "
                    "future signed-upload path."
                ),
            ),
        )

    def _mark_chunk_uploaded(
        self,
        meeting: MeetingDetail,
        chunk: CaptureChunkSummary,
    ) -> None:
        recorded_at = chunk.recordedAt
        chunk.lifecycleStatus = "uploaded"
        chunk.uploadStatus = "uploaded"
        meeting.latestEvents.insert(
            0,
            LiveEvent(
                id=f"evt_{uuid4().hex[:12]}",
                kind="capture",
                at=recorded_at,
                title=f"Chunk {chunk.sequence} upload acknowledged",
                detail=(
                    "The local development pipeline marks the upload stage complete "
                    "before mock processing continues."
                ),
            ),
        )

    def _prepare_chunk_processing(
        self,
        meeting: MeetingDetail,
        chunk: CaptureChunkSummary,
    ) -> ChunkContext:
        recorded_at = chunk.recordedAt
        chunk_key = (meeting.id, chunk.clientChunkId)
        media = self._chunk_media_by_client_id.pop(chunk_key, None)
        if media is not None:
            # Real Gemini multimodal pass over the captured screen + audio.
            media_bytes, media_mime = media
            frame_count, screen_events, transcript_segments, vision_source = analyze_chunk_media(
                chunk, media_bytes, media_mime
            )
            typed_source: ProcessingSourceMode = (
                "downstream_service" if vision_source == "gemini_vision" else "local_fallback"
            )
            transcript_source = typed_source
            media_source = typed_source
        else:
            # No media uploaded for this chunk — deterministic template fallback.
            transcript_segments, transcript_source = process_transcript_chunk_with_source(chunk)
            frame_count, screen_events, media_source = process_media_chunk_with_source(chunk)
        final_end = transcript_segments[-1].endedAt

        meeting.recentTranscriptSegments = (
            list(reversed(transcript_segments)) + meeting.recentTranscriptSegments
        )[:10]
        meeting.metrics.transcriptSegmentsCount += len(transcript_segments)
        meeting.recentScreenEvents = (list(reversed(screen_events)) + meeting.recentScreenEvents)[
            :10
        ]
        meeting.metrics.visualEventsCount += len(screen_events)
        chunk.lifecycleStatus = "processing"
        chunk.processingStatus = "processing"
        chunk.frameCount = frame_count
        chunk.transcriptSegmentCount = len(transcript_segments)
        chunk.visualEventCount = len(screen_events)
        chunk.transcriptSource = transcript_source
        chunk.mediaSource = media_source
        meeting.latestEvents.insert(
            0,
            LiveEvent(
                id=f"evt_{uuid4().hex[:12]}",
                kind="transcript",
                at=final_end,
                title=f"Transcript extracted for chunk {chunk.sequence}",
                detail=(
                    f"{transcript_segments[0].speakerLabel} and {transcript_segments[-1].speakerLabel} "
                    "segments were produced from the capture window."
                ),
            ),
        )
        meeting.latestEvents.insert(
            0,
            LiveEvent(
                id=f"evt_{uuid4().hex[:12]}",
                kind="capture",
                at=recorded_at,
                title=f"Visual evidence extracted for chunk {chunk.sequence}",
                detail=(
                    f"{len(screen_events)} screen events were derived from "
                    f"{frame_count} extracted frames."
                ),
            ),
        )
        meeting.latestEvents.insert(
            0,
            LiveEvent(
                id=f"evt_{uuid4().hex[:12]}",
                kind="capture",
                at=final_end,
                title=f"Chunk {chunk.sequence} ready for reasoning",
                detail=(
                    "Deterministic transcript and media processing completed. "
                    "The reasoning step can now run independently."
                ),
            ),
        )
        chunk_context = ChunkContext(
            chunk=chunk.model_copy(deep=True),
            transcriptSegments=[segment.model_copy(deep=True) for segment in transcript_segments],
            screenEvents=[screen_event.model_copy(deep=True) for screen_event in screen_events],
        )
        self._chunk_context_by_client_id[(meeting.id, chunk.clientChunkId)] = chunk_context
        return chunk_context

    def _finalize_chunk_reasoning(
        self,
        meeting: MeetingDetail,
        chunk: CaptureChunkSummary,
        chunk_context: ChunkContext,
    ) -> None:
        template_index = (chunk.sequence - 1) % len(DECISION_TEMPLATES)
        transcript_segments = chunk_context.transcriptSegments
        screen_events = chunk_context.screenEvents
        final_end = transcript_segments[-1].endedAt
        evidence_refs = self._build_evidence_references(
            chunk,
            transcript_segments,
            screen_events,
        )
        chunk_insight = build_chunk_insight(
            meeting=meeting.model_copy(deep=True),
            meeting_state=self._build_meeting_state(meeting),
            chunk_context=ChunkContext(
                chunk=chunk.model_copy(deep=True),
                transcriptSegments=[segment.model_copy(deep=True) for segment in transcript_segments],
                screenEvents=[screen_event.model_copy(deep=True) for screen_event in screen_events],
            ),
        )
        agent_outputs, reasoning_source = run_chunk_reasoning_with_source(chunk_insight)
        chunk.reasoningSource = reasoning_source
        if agent_outputs is not None:
            signal_count = self._apply_agent_outputs_to_meeting(
                meeting=meeting,
                payload=agent_outputs,
                source_chunk=chunk,
                recorded_at=final_end,
                evidence_refs=evidence_refs,
            )
            chunk.lifecycleStatus = "processed"
            chunk.processingStatus = "processed"
            chunk.signalCount = signal_count
            self._chunk_context_by_client_id[(meeting.id, chunk.clientChunkId)] = ChunkContext(
                chunk=chunk.model_copy(deep=True),
                transcriptSegments=[segment.model_copy(deep=True) for segment in transcript_segments],
                screenEvents=[screen_event.model_copy(deep=True) for screen_event in screen_events],
            )
            return

        decision_title, decision_rationale = DECISION_TEMPLATES[template_index]
        decision = self._upsert_decision(
            meeting,
            title=decision_title,
            rationale=decision_rationale,
            speaker_label=transcript_segments[-1].speakerLabel,
            recorded_at=final_end,
            chunk_client_id=chunk.clientChunkId,
            evidence_refs=evidence_refs,
        )
        meeting.latestEvents.insert(
            0,
            LiveEvent(
                id=f"evt_{uuid4().hex[:12]}",
                kind="decision",
                at=final_end,
                title="Reasoning agent drafted a decision",
                detail=decision.title,
            ),
        )

        signal_count = 1

        if chunk.sequence % 2 == 1:
            owner_label, action, due_hint = COMMITMENT_TEMPLATES[template_index]
            commitment = self._upsert_commitment(
                meeting,
                owner_label=owner_label,
                action=action,
                due_hint=due_hint,
                recorded_at=final_end,
                chunk_client_id=chunk.clientChunkId,
                evidence_refs=evidence_refs,
            )
            meeting.latestEvents.insert(
                0,
                LiveEvent(
                    id=f"evt_{uuid4().hex[:12]}",
                    kind="commitment",
                    at=final_end,
                    title="Commitment recorded",
                    detail=f"{commitment.ownerLabel}: {commitment.action}",
                ),
            )
            signal_count += 1

        if chunk.sequence % 3 != 0:
            blocker_summary, blocker_severity, blocker_owner = BLOCKER_TEMPLATES[template_index]
            blocker = self._upsert_blocker(
                meeting,
                summary=blocker_summary,
                severity=blocker_severity,
                owner_label=blocker_owner,
                recorded_at=final_end,
                chunk_client_id=chunk.clientChunkId,
                evidence_refs=evidence_refs,
            )
            meeting.latestEvents.insert(
                0,
                LiveEvent(
                    id=f"evt_{uuid4().hex[:12]}",
                    kind="blocker",
                    at=final_end,
                    title="Blocker flagged",
                    detail=f"{blocker.summary} Owner: {blocker.ownerLabel}.",
                ),
            )
            signal_count += 1

        (
            source_meeting_id,
            memory_summary,
            source_meeting_title,
            strength,
            relation,
            score,
            snippet,
        ) = MEMORY_TEMPLATES[template_index]
        memory_match = MemoryMatch(
            id=f"mem_{uuid4().hex[:12]}",
            sourceMeetingId=source_meeting_id,
            summary=memory_summary,
            sourceMeetingTitle=source_meeting_title,
            strength=strength,
            relation=relation,
            score=score,
            snippet=snippet,
            recordedAt=final_end,
        )
        meeting.recentMemoryMatches.insert(0, memory_match)
        meeting.recentMemoryMatches = meeting.recentMemoryMatches[:6]
        meeting.metrics.memoryMatchesCount += 1
        meeting.latestEvents.insert(
            0,
            LiveEvent(
                id=f"evt_{uuid4().hex[:12]}",
                kind="memory",
                at=final_end,
                title="Elastic memory match attached",
                detail=f"{memory_match.summary} Source: {memory_match.sourceMeetingTitle}.",
            ),
        )
        signal_count += 1

        open_question = self._upsert_open_question(
            meeting,
            question=OPEN_QUESTION_TEMPLATES[template_index],
            speaker_label=transcript_segments[-1].speakerLabel,
            recorded_at=final_end,
            chunk_client_id=chunk.clientChunkId,
            evidence_refs=evidence_refs,
        )
        meeting.latestEvents.insert(
            0,
            LiveEvent(
                id=f"evt_{uuid4().hex[:12]}",
                kind="decision",
                at=final_end,
                title="Open question captured",
                detail=open_question.question,
            ),
        )
        signal_count += 1

        chunk.lifecycleStatus = "processed"
        chunk.processingStatus = "processed"
        chunk.signalCount = signal_count
        self._chunk_context_by_client_id[(meeting.id, chunk.clientChunkId)] = ChunkContext(
            chunk=chunk.model_copy(deep=True),
            transcriptSegments=[segment.model_copy(deep=True) for segment in transcript_segments],
            screenEvents=[screen_event.model_copy(deep=True) for screen_event in screen_events],
        )

    def _apply_agent_outputs_to_meeting(
        self,
        meeting: MeetingDetail,
        payload: RegisterAgentOutputsRequest,
        source_chunk: CaptureChunkSummary,
        recorded_at: datetime,
        evidence_refs: list[EvidenceReference],
    ) -> int:
        self._persist_decisions(
            meeting,
            payload.decisions,
            recorded_at,
            source_chunk.clientChunkId,
            evidence_refs,
        )
        self._persist_commitments(
            meeting,
            payload.commitments,
            recorded_at,
            source_chunk.clientChunkId,
            evidence_refs,
        )
        self._persist_blockers(
            meeting,
            payload.blockers,
            recorded_at,
            source_chunk.clientChunkId,
            evidence_refs,
        )
        self._persist_open_questions(
            meeting,
            payload.openQuestions,
            recorded_at,
            source_chunk.clientChunkId,
            evidence_refs,
        )
        resolved_count = 0
        resolved_count += self._resolve_decisions(
            meeting,
            payload.resolvedDecisionIds,
            recorded_at,
            source_chunk.clientChunkId,
            evidence_refs,
        )
        resolved_count += self._resolve_commitments(
            meeting,
            payload.resolvedCommitmentIds,
            recorded_at,
            source_chunk.clientChunkId,
            evidence_refs,
        )
        resolved_count += self._resolve_blockers(
            meeting,
            payload.resolvedBlockerIds,
            recorded_at,
            source_chunk.clientChunkId,
            evidence_refs,
        )
        resolved_count += self._resolve_open_questions(
            meeting,
            payload.resolvedOpenQuestionIds,
            recorded_at,
            source_chunk.clientChunkId,
            evidence_refs,
        )
        self._persist_memory_matches(meeting, payload.memoryMatches, recorded_at)
        return (
            len(payload.decisions)
            + len(payload.commitments)
            + len(payload.blockers)
            + len(payload.openQuestions)
            + len(payload.memoryMatches)
            + resolved_count
        )

    def _build_meeting_state(self, meeting: MeetingDetail) -> MeetingStateSnapshot:
        latest_chunk_client_id = (
            meeting.recentCaptureChunks[0].clientChunkId
            if meeting.recentCaptureChunks
            else None
        )
        active_capture_session_id = (
            meeting.activeCaptureSession.id if meeting.activeCaptureSession is not None else None
        )
        return MeetingStateSnapshot(
            meetingId=meeting.id,
            meetingStatus=meeting.status,
            activeCaptureSessionId=active_capture_session_id,
            latestChunkClientId=latest_chunk_client_id,
            openDecisions=[
                decision.model_copy(deep=True)
                for decision in meeting.recentDecisions
                if decision.status != "resolved"
            ],
            openCommitments=[
                commitment.model_copy(deep=True) for commitment in meeting.recentCommitments
                if commitment.status != "resolved"
            ],
            openBlockers=[
                blocker.model_copy(deep=True)
                for blocker in meeting.recentBlockers
                if blocker.status != "resolved"
            ],
            openQuestions=[
                open_question.model_copy(deep=True)
                for open_question in meeting.recentOpenQuestions
                if open_question.status != "resolved"
            ],
        )

    def _mark_meeting_updated(self, meeting_id: str) -> None:
        self._meeting_revisions[meeting_id] = self._meeting_revisions.get(meeting_id, 0) + 1

    def _build_final_report(self, meeting: MeetingDetail) -> FinalReport:
        summary_parts = [
            f"{meeting.title} captured {len(meeting.recentDecisions)} decisions,",
            f"{len(meeting.recentCommitments)} commitments, and",
            f"{len(meeting.recentBlockers)} blockers.",
        ]
        if meeting.recentOpenQuestions:
            summary_parts.append(
                f"{len(meeting.recentOpenQuestions)} open questions remain for follow-up."
            )
        if meeting.recentMemoryMatches:
            summary_parts.append(
                "Historical memory matches were attached to help the team spot recurring issues."
            )

        return FinalReport(
            meetingId=meeting.id,
            generatedAt=_utc_now(),
            executiveSummary=" ".join(summary_parts),
            decisions=[decision.model_copy(deep=True) for decision in meeting.recentDecisions],
            commitments=[
                commitment.model_copy(deep=True) for commitment in meeting.recentCommitments
            ],
            blockers=[blocker.model_copy(deep=True) for blocker in meeting.recentBlockers],
            openQuestions=[
                open_question.model_copy(deep=True)
                for open_question in meeting.recentOpenQuestions
            ],
            memoryHighlights=[
                memory_match.model_copy(deep=True)
                for memory_match in meeting.recentMemoryMatches
            ],
        )

    def _persist_decisions(
        self,
        meeting: MeetingDetail,
        decisions: list[AgentDecisionInput],
        recorded_at: datetime,
        chunk_client_id: str,
        evidence_refs: list[EvidenceReference],
    ) -> None:
        for draft in decisions:
            self._upsert_decision(
                meeting,
                title=draft.title,
                rationale=draft.rationale,
                speaker_label=draft.speakerLabel,
                recorded_at=recorded_at,
                chunk_client_id=chunk_client_id,
                evidence_refs=evidence_refs,
            )

    def _persist_commitments(
        self,
        meeting: MeetingDetail,
        commitments: list[AgentCommitmentInput],
        recorded_at: datetime,
        chunk_client_id: str,
        evidence_refs: list[EvidenceReference],
    ) -> None:
        for draft in commitments:
            self._upsert_commitment(
                meeting,
                owner_label=draft.ownerLabel,
                action=draft.action,
                due_hint=draft.dueHint,
                recorded_at=recorded_at,
                chunk_client_id=chunk_client_id,
                evidence_refs=evidence_refs,
            )

    def _persist_blockers(
        self,
        meeting: MeetingDetail,
        blockers: list[AgentBlockerInput],
        recorded_at: datetime,
        chunk_client_id: str,
        evidence_refs: list[EvidenceReference],
    ) -> None:
        for draft in blockers:
            self._upsert_blocker(
                meeting,
                summary=draft.summary,
                severity=draft.severity,
                owner_label=draft.ownerLabel,
                recorded_at=recorded_at,
                chunk_client_id=chunk_client_id,
                evidence_refs=evidence_refs,
            )

    def _persist_open_questions(
        self,
        meeting: MeetingDetail,
        open_questions: list[AgentOpenQuestionInput],
        recorded_at: datetime,
        chunk_client_id: str,
        evidence_refs: list[EvidenceReference],
    ) -> None:
        for draft in open_questions:
            self._upsert_open_question(
                meeting,
                question=draft.question,
                speaker_label=draft.speakerLabel,
                recorded_at=recorded_at,
                chunk_client_id=chunk_client_id,
                evidence_refs=evidence_refs,
            )

    def _resolve_decisions(
        self,
        meeting: MeetingDetail,
        decision_ids: list[str],
        recorded_at: datetime,
        chunk_client_id: str,
        evidence_refs: list[EvidenceReference],
    ) -> int:
        return self._resolve_reasoning_records(
            meeting_id=meeting.id,
            records=meeting.recentDecisions,
            record_ids=decision_ids,
            recorded_at=recorded_at,
            chunk_client_id=chunk_client_id,
            evidence_refs=evidence_refs,
        )

    def _resolve_commitments(
        self,
        meeting: MeetingDetail,
        commitment_ids: list[str],
        recorded_at: datetime,
        chunk_client_id: str,
        evidence_refs: list[EvidenceReference],
    ) -> int:
        return self._resolve_reasoning_records(
            meeting_id=meeting.id,
            records=meeting.recentCommitments,
            record_ids=commitment_ids,
            recorded_at=recorded_at,
            chunk_client_id=chunk_client_id,
            evidence_refs=evidence_refs,
        )

    def _resolve_blockers(
        self,
        meeting: MeetingDetail,
        blocker_ids: list[str],
        recorded_at: datetime,
        chunk_client_id: str,
        evidence_refs: list[EvidenceReference],
    ) -> int:
        return self._resolve_reasoning_records(
            meeting_id=meeting.id,
            records=meeting.recentBlockers,
            record_ids=blocker_ids,
            recorded_at=recorded_at,
            chunk_client_id=chunk_client_id,
            evidence_refs=evidence_refs,
        )

    def _resolve_open_questions(
        self,
        meeting: MeetingDetail,
        open_question_ids: list[str],
        recorded_at: datetime,
        chunk_client_id: str,
        evidence_refs: list[EvidenceReference],
    ) -> int:
        return self._resolve_reasoning_records(
            meeting_id=meeting.id,
            records=meeting.recentOpenQuestions,
            record_ids=open_question_ids,
            recorded_at=recorded_at,
            chunk_client_id=chunk_client_id,
            evidence_refs=evidence_refs,
        )

    def _upsert_decision(
        self,
        meeting: MeetingDetail,
        title: str,
        rationale: str,
        speaker_label: str,
        recorded_at: datetime,
        chunk_client_id: str,
        evidence_refs: list[EvidenceReference],
    ) -> DecisionRecord:
        record = self._upsert_reasoning_record(
            meeting=meeting,
            records=meeting.recentDecisions,
            metric_attr="decisionsCount",
            key=self._normalize_key(title),
            make_record=lambda: DecisionRecord(
                id=f"dec_{uuid4().hex[:12]}",
                title=title,
                rationale=rationale,
                speakerLabel=speaker_label,
                status="open",
                firstSeenChunkId=chunk_client_id,
                lastUpdatedChunkId=chunk_client_id,
                recordedAt=recorded_at,
                evidence=self._clone_evidence(evidence_refs),
            ),
            update_record=lambda record: record.model_copy(
                update={
                    "title": title,
                    "rationale": rationale,
                    "speakerLabel": speaker_label,
                    "status": self._next_record_status(record.status),
                    "lastUpdatedChunkId": chunk_client_id,
                    "recordedAt": recorded_at,
                    "evidence": self._clone_evidence(evidence_refs),
                }
            ),
            key_getter=lambda record: self._normalize_key(record.title),
        )
        self._index_decision(meeting.id, record)
        return record

    def _upsert_commitment(
        self,
        meeting: MeetingDetail,
        owner_label: str,
        action: str,
        due_hint: str,
        recorded_at: datetime,
        chunk_client_id: str,
        evidence_refs: list[EvidenceReference],
    ) -> CommitmentRecord:
        record = self._upsert_reasoning_record(
            meeting=meeting,
            records=meeting.recentCommitments,
            metric_attr="commitmentsCount",
            key=self._normalize_key(owner_label, action),
            make_record=lambda: CommitmentRecord(
                id=f"cmt_{uuid4().hex[:12]}",
                ownerLabel=owner_label,
                action=action,
                dueHint=due_hint,
                status="open",
                firstSeenChunkId=chunk_client_id,
                lastUpdatedChunkId=chunk_client_id,
                recordedAt=recorded_at,
                evidence=self._clone_evidence(evidence_refs),
            ),
            update_record=lambda record: record.model_copy(
                update={
                    "ownerLabel": owner_label,
                    "action": action,
                    "dueHint": due_hint,
                    "status": self._next_record_status(record.status),
                    "lastUpdatedChunkId": chunk_client_id,
                    "recordedAt": recorded_at,
                    "evidence": self._clone_evidence(evidence_refs),
                }
            ),
            key_getter=lambda record: self._normalize_key(record.ownerLabel, record.action),
        )
        self._index_commitment(meeting.id, record)
        return record

    def _upsert_blocker(
        self,
        meeting: MeetingDetail,
        summary: str,
        severity: str,
        owner_label: str,
        recorded_at: datetime,
        chunk_client_id: str,
        evidence_refs: list[EvidenceReference],
    ) -> BlockerRecord:
        record = self._upsert_reasoning_record(
            meeting=meeting,
            records=meeting.recentBlockers,
            metric_attr="blockersCount",
            key=self._normalize_key(summary),
            make_record=lambda: BlockerRecord(
                id=f"blk_{uuid4().hex[:12]}",
                summary=summary,
                severity=severity,
                ownerLabel=owner_label,
                status="open",
                firstSeenChunkId=chunk_client_id,
                lastUpdatedChunkId=chunk_client_id,
                recordedAt=recorded_at,
                evidence=self._clone_evidence(evidence_refs),
            ),
            update_record=lambda record: record.model_copy(
                update={
                    "summary": summary,
                    "severity": severity,
                    "ownerLabel": owner_label,
                    "status": self._next_record_status(record.status),
                    "lastUpdatedChunkId": chunk_client_id,
                    "recordedAt": recorded_at,
                    "evidence": self._clone_evidence(evidence_refs),
                }
            ),
            key_getter=lambda record: self._normalize_key(record.summary),
        )
        self._index_blocker(meeting.id, record)
        return record

    def _upsert_open_question(
        self,
        meeting: MeetingDetail,
        question: str,
        speaker_label: str,
        recorded_at: datetime,
        chunk_client_id: str,
        evidence_refs: list[EvidenceReference],
    ) -> OpenQuestionRecord:
        record = self._upsert_reasoning_record(
            meeting=meeting,
            records=meeting.recentOpenQuestions,
            metric_attr="openQuestionsCount",
            key=self._normalize_key(question),
            make_record=lambda: OpenQuestionRecord(
                id=f"oqn_{uuid4().hex[:12]}",
                question=question,
                speakerLabel=speaker_label,
                status="open",
                firstSeenChunkId=chunk_client_id,
                lastUpdatedChunkId=chunk_client_id,
                recordedAt=recorded_at,
                evidence=self._clone_evidence(evidence_refs),
            ),
            update_record=lambda record: record.model_copy(
                update={
                    "question": question,
                    "speakerLabel": speaker_label,
                    "status": self._next_record_status(record.status),
                    "lastUpdatedChunkId": chunk_client_id,
                    "recordedAt": recorded_at,
                    "evidence": self._clone_evidence(evidence_refs),
                }
            ),
            key_getter=lambda record: self._normalize_key(record.question),
        )
        self._index_open_question(meeting.id, record)
        return record

    def _upsert_reasoning_record(
        self,
        meeting: MeetingDetail,
        records: list,
        metric_attr: str,
        key: str,
        make_record: Callable[[], object],
        update_record: Callable[[object], object],
        key_getter: Callable[[object], str],
    ):
        for index, record in enumerate(records):
            if key_getter(record) != key:
                continue
            updated_record = update_record(record)
            records.pop(index)
            records.insert(0, updated_record)
            del records[6:]
            return updated_record

        created_record = make_record()
        records.insert(0, created_record)
        del records[6:]
        current_value = getattr(meeting.metrics, metric_attr)
        setattr(meeting.metrics, metric_attr, current_value + 1)
        return created_record

    def _resolve_reasoning_records(
        self,
        meeting_id: str,
        records: list,
        record_ids: list[str],
        recorded_at: datetime,
        chunk_client_id: str,
        evidence_refs: list[EvidenceReference],
    ) -> int:
        resolved_count = 0
        for target_id in record_ids:
            for index, record in enumerate(records):
                if record.id != target_id or record.status == "resolved":
                    continue
                updated_record = record.model_copy(
                    update={
                        "status": "resolved",
                        "lastUpdatedChunkId": chunk_client_id,
                        "recordedAt": recorded_at,
                        "evidence": self._clone_evidence(evidence_refs),
                    }
                )
                records.pop(index)
                records.insert(0, updated_record)
                self._index_record(meeting_id, updated_record)
                resolved_count += 1
                break
        del records[6:]
        return resolved_count

    def _build_evidence_references(
        self,
        chunk: CaptureChunkSummary,
        transcript_segments: list,
        screen_events: list,
    ) -> list[EvidenceReference]:
        evidence_refs: list[EvidenceReference] = []

        for segment in transcript_segments[:2]:
            start_ms = max(
                int((segment.startedAt - chunk.recordedAt).total_seconds() * 1000),
                0,
            )
            end_ms = max(
                int((segment.endedAt - chunk.recordedAt).total_seconds() * 1000),
                start_ms,
            )
            evidence_refs.append(
                EvidenceReference(
                    chunkId=chunk.id,
                    clientChunkId=chunk.clientChunkId,
                    tStartMs=start_ms,
                    tEndMs=end_ms,
                    transcriptRef=segment.id,
                    frameRef=None,
                    note=f"{segment.speakerLabel}: {segment.text}",
                )
            )

        if screen_events:
            primary_screen_event = screen_events[0]
            screen_end_ms = min(
                chunk.durationMs,
                primary_screen_event.frameTimestampMs + 1000,
            )
            evidence_refs.append(
                EvidenceReference(
                    chunkId=chunk.id,
                    clientChunkId=chunk.clientChunkId,
                    tStartMs=primary_screen_event.frameTimestampMs,
                    tEndMs=max(screen_end_ms, primary_screen_event.frameTimestampMs),
                    transcriptRef=None,
                    frameRef=primary_screen_event.id,
                    note=primary_screen_event.summary,
                )
            )

        if not evidence_refs:
            evidence_refs.append(
                EvidenceReference(
                    chunkId=chunk.id,
                    clientChunkId=chunk.clientChunkId,
                    tStartMs=0,
                    tEndMs=chunk.durationMs,
                    transcriptRef=None,
                    frameRef=None,
                    note="The capture chunk was processed without transcript or frame-level references.",
                )
            )

        return evidence_refs[:4]

    def _clone_evidence(
        self,
        evidence_refs: list[EvidenceReference],
    ) -> list[EvidenceReference]:
        return [reference.model_copy(deep=True) for reference in evidence_refs]

    def _copy_indexed_outcomes_for_meeting(
        self,
        meeting_id: str,
    ) -> list[IndexedOutcomeDocument]:
        documents = [
            document.model_copy(deep=True)
            for (document_meeting_id, _), document in self._indexed_outcomes.items()
            if document_meeting_id == meeting_id
        ]
        documents.sort(key=lambda document: document.updatedAt, reverse=True)
        return documents

    def _sync_indexed_outcomes_to_elastic(
        self,
        meeting: MeetingDetail | None,
        documents: list[IndexedOutcomeDocument],
    ) -> None:
        if meeting is None or len(documents) == 0:
            return
        upsert_indexed_outcomes_to_elasticsearch(
            config=settings,
            meeting=meeting,
            documents=documents,
        )

    def _build_empty_memory_match(
        self,
        meeting: MeetingDetail,
    ) -> MemoryMatch:
        return MemoryMatch(
            id=f"mem_{uuid4().hex[:12]}",
            sourceMeetingId=f"{meeting.id}_new_signal",
            summary="No strong historical match was found for this candidate outcome.",
            sourceMeetingTitle=meeting.title,
            strength="related",
            relation="new",
            score=0.12,
            snippet="The current development memory layer did not return a strong historical precedent.",
            recordedAt=_utc_now(),
        )

    def _resolve_chunk_memory_matches(
        self,
        *,
        meeting_id: str,
        memory_queries: list[SearchPriorOutcomesRequest],
    ) -> list[MemoryMatch]:
        if len(memory_queries) == 0:
            return []

        matches: list[MemoryMatch] = []
        seen: set[tuple[str, str, str, str]] = set()
        for query in memory_queries[:3]:
            query_matches = self.search_prior_outcomes(meeting_id, query)
            if query_matches is None:
                continue
            for match in query_matches:
                if self._is_placeholder_memory_match(match):
                    continue
                dedupe_key = (
                    match.sourceMeetingId,
                    match.summary,
                    match.relation,
                    match.snippet,
                )
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                matches.append(match.model_copy(deep=True))
                if len(matches) >= 6:
                    return matches
        return matches

    def _is_placeholder_memory_match(self, match: MemoryMatch) -> bool:
        return (
            match.sourceMeetingId.endswith("_new_signal")
            and match.summary.startswith("No strong historical match was found")
        )

    def _index_decision(self, meeting_id: str, record: DecisionRecord) -> None:
        self._indexed_outcomes[(meeting_id, record.id)] = IndexedOutcomeDocument(
            id=record.id,
            meetingId=meeting_id,
            recordType="decision",
            summary=record.title,
            detail=record.rationale,
            status=record.status,
            ownerLabel=None,
            speakerLabel=record.speakerLabel,
            dueHint=None,
            severity=None,
            firstSeenChunkId=record.firstSeenChunkId,
            lastUpdatedChunkId=record.lastUpdatedChunkId,
            createdAt=record.recordedAt,
            updatedAt=record.recordedAt,
            evidence=self._clone_evidence(record.evidence),
        )

    def _index_commitment(self, meeting_id: str, record: CommitmentRecord) -> None:
        self._indexed_outcomes[(meeting_id, record.id)] = IndexedOutcomeDocument(
            id=record.id,
            meetingId=meeting_id,
            recordType="commitment",
            summary=record.action,
            detail=f"{record.ownerLabel} committed to {record.action} with due hint {record.dueHint}.",
            status=record.status,
            ownerLabel=record.ownerLabel,
            speakerLabel=None,
            dueHint=record.dueHint,
            severity=None,
            firstSeenChunkId=record.firstSeenChunkId,
            lastUpdatedChunkId=record.lastUpdatedChunkId,
            createdAt=record.recordedAt,
            updatedAt=record.recordedAt,
            evidence=self._clone_evidence(record.evidence),
        )

    def _index_blocker(self, meeting_id: str, record: BlockerRecord) -> None:
        self._indexed_outcomes[(meeting_id, record.id)] = IndexedOutcomeDocument(
            id=record.id,
            meetingId=meeting_id,
            recordType="blocker",
            summary=record.summary,
            detail=f"Severity {record.severity}; owner {record.ownerLabel}.",
            status=record.status,
            ownerLabel=record.ownerLabel,
            speakerLabel=None,
            dueHint=None,
            severity=record.severity,
            firstSeenChunkId=record.firstSeenChunkId,
            lastUpdatedChunkId=record.lastUpdatedChunkId,
            createdAt=record.recordedAt,
            updatedAt=record.recordedAt,
            evidence=self._clone_evidence(record.evidence),
        )

    def _index_open_question(self, meeting_id: str, record: OpenQuestionRecord) -> None:
        self._indexed_outcomes[(meeting_id, record.id)] = IndexedOutcomeDocument(
            id=record.id,
            meetingId=meeting_id,
            recordType="open_question",
            summary=record.question,
            detail=f"Open question raised by {record.speakerLabel}.",
            status=record.status,
            ownerLabel=None,
            speakerLabel=record.speakerLabel,
            dueHint=None,
            severity=None,
            firstSeenChunkId=record.firstSeenChunkId,
            lastUpdatedChunkId=record.lastUpdatedChunkId,
            createdAt=record.recordedAt,
            updatedAt=record.recordedAt,
            evidence=self._clone_evidence(record.evidence),
        )

    def _index_record(
        self,
        meeting_id: str,
        record,
    ) -> None:
        if isinstance(record, DecisionRecord):
            self._index_decision(meeting_id, record)
        elif isinstance(record, CommitmentRecord):
            self._index_commitment(meeting_id, record)
        elif isinstance(record, BlockerRecord):
            self._index_blocker(meeting_id, record)
        elif isinstance(record, OpenQuestionRecord):
            self._index_open_question(meeting_id, record)

    def _next_record_status(self, current_status: str) -> str:
        if current_status == "resolved":
            return "reopened"
        if current_status == "open":
            return "updated"
        return current_status

    def _normalize_key(self, *parts: str) -> str:
        return "||".join(part.strip().lower() for part in parts)

    def _persist_memory_matches(
        self,
        meeting: MeetingDetail,
        memory_matches: list[AgentMemoryMatchInput],
        recorded_at: datetime,
    ) -> None:
        for draft in memory_matches:
            memory_match = MemoryMatch(
                id=f"mem_{uuid4().hex[:12]}",
                sourceMeetingId=draft.sourceMeetingId,
                summary=draft.summary,
                sourceMeetingTitle=draft.sourceMeetingTitle,
                strength=draft.strength,
                relation=draft.relation,
                score=draft.score,
                snippet=draft.snippet,
                recordedAt=recorded_at,
            )
            meeting.recentMemoryMatches.insert(0, memory_match)
            meeting.metrics.memoryMatchesCount += 1
        meeting.recentMemoryMatches = meeting.recentMemoryMatches[:6]

    def generate_action_recommendations(self, meeting_id: str) -> list[ActionRecommendation] | None:
        with self._lock:
            meeting = self._meetings.get(meeting_id)
            if meeting is None:
                return None
            report = self._final_reports.get(meeting_id)
            if report is None:
                return None
            meeting_copy = meeting.model_copy(deep=True)
            report_copy = report.model_copy(deep=True)

        agent_inputs, source = run_action_agent_with_source(report_copy, meeting_copy.title)
        if agent_inputs is None:
            return []

        recommendations: list[ActionRecommendation] = []
        with self._lock:
            meeting = self._meetings.get(meeting_id)
            if meeting is None:
                return None
            recorded_at = _utc_now()
            for agent_input in agent_inputs:
                recommendation = self._build_action_recommendation(
                    meeting_id=meeting_id,
                    agent_input=agent_input,
                    recorded_at=recorded_at,
                )
                self._action_recommendations[(meeting_id, recommendation.id)] = recommendation
                meeting.recentActionRecommendations.insert(0, recommendation)
                meeting.metrics.actionRecommendationsCount += 1
                recommendations.append(recommendation)
            meeting.recentActionRecommendations = meeting.recentActionRecommendations[:20]
            self._mark_meeting_updated(meeting_id)
            return [r.model_copy(deep=True) for r in recommendations]

    def list_action_recommendations(
        self,
        meeting_id: str,
    ) -> list[ActionRecommendation] | None:
        with self._lock:
            if meeting_id not in self._meetings:
                return None
            recommendations = [
                rec.model_copy(deep=True)
                for (rec_meeting_id, _), rec in self._action_recommendations.items()
                if rec_meeting_id == meeting_id
            ]
            recommendations.sort(key=lambda r: r.createdAt, reverse=True)
            return recommendations

    def approve_action(
        self,
        meeting_id: str,
        recommendation_id: str,
        request: ActionApprovalRequest,
    ) -> ActionRecommendation | None:
        with self._lock:
            meeting = self._meetings.get(meeting_id)
            if meeting is None:
                return None
            recommendation = self._action_recommendations.get((meeting_id, recommendation_id))
            if recommendation is None:
                return None
            recommendation.status = "approved"
            recommendation.updatedAt = _utc_now()
            self._update_meeting_recommendation(meeting, recommendation)
            self._mark_meeting_updated(meeting_id)
            return recommendation.model_copy(deep=True)

    def reject_action(
        self,
        meeting_id: str,
        recommendation_id: str,
        request: ActionApprovalRequest,
    ) -> ActionRecommendation | None:
        with self._lock:
            meeting = self._meetings.get(meeting_id)
            if meeting is None:
                return None
            recommendation = self._action_recommendations.get((meeting_id, recommendation_id))
            if recommendation is None:
                return None
            recommendation.status = "rejected"
            recommendation.updatedAt = _utc_now()
            self._update_meeting_recommendation(meeting, recommendation)
            self._mark_meeting_updated(meeting_id)
            return recommendation.model_copy(deep=True)

    def execute_action(
        self,
        meeting_id: str,
        recommendation_id: str,
    ) -> ActionExecutionResult | None:
        with self._lock:
            meeting = self._meetings.get(meeting_id)
            if meeting is None:
                return None
            recommendation = self._action_recommendations.get((meeting_id, recommendation_id))
            if recommendation is None:
                return None
            if recommendation.status != "approved":
                return None

        success = False
        detail = "Unknown action type"
        if recommendation.type.startswith("jira_"):
            success, detail = execute_jira_action(recommendation)
        elif recommendation.type.startswith("slack_"):
            success, detail = execute_slack_action(recommendation)

        with self._lock:
            recommendation = self._action_recommendations.get((meeting_id, recommendation_id))
            if recommendation is None:
                return None
            recommendation.status = "executed" if success else "failed"
            recommendation.executedAt = _utc_now()
            recommendation.executionResult = detail
            recommendation.updatedAt = _utc_now()
            self._update_meeting_recommendation(meeting, recommendation)
            self._mark_meeting_updated(meeting_id)

        return ActionExecutionResult(
            recommendationId=recommendation_id,
            status="executed" if success else "failed",
            detail=detail,
            executedAt=recommendation.executedAt,
        )

    def _build_action_recommendation(
        self,
        meeting_id: str,
        agent_input: ActionRecommendationInput,
        recorded_at: datetime,
    ) -> ActionRecommendation:
        jira_details = None
        if agent_input.jiraDetails is not None:
            jira_details = JiraRecommendation(
                action=agent_input.jiraDetails.action,
                issueType=agent_input.jiraDetails.issueType,
                title=agent_input.jiraDetails.title,
                description=agent_input.jiraDetails.description,
                priority=agent_input.jiraDetails.priority,
                ownerLabel=agent_input.jiraDetails.ownerLabel,
                evidence=[
                    EvidenceReference.model_validate(ref) if isinstance(ref, dict) else ref
                    for ref in agent_input.jiraDetails.evidence
                ],
                confidence=agent_input.jiraDetails.confidence,
            )
        slack_details = None
        if agent_input.slackDetails is not None:
            slack_details = SlackRecommendation(
                type=agent_input.slackDetails.type,
                channel=agent_input.slackDetails.channel,
                title=agent_input.slackDetails.title,
                message=agent_input.slackDetails.message,
                evidence=[
                    EvidenceReference.model_validate(ref) if isinstance(ref, dict) else ref
                    for ref in agent_input.slackDetails.evidence
                ],
                confidence=agent_input.slackDetails.confidence,
            )
        return ActionRecommendation(
            id=f"act_{uuid4().hex[:12]}",
            meetingId=meeting_id,
            type=agent_input.type,
            status="pending",
            urgency=agent_input.urgency,
            confidence=agent_input.confidence,
            jiraDetails=jira_details,
            slackDetails=slack_details,
            evidence=[
                EvidenceReference.model_validate(ref) if isinstance(ref, dict) else ref
                for ref in agent_input.evidence
            ],
            createdAt=recorded_at,
            updatedAt=recorded_at,
            executedAt=None,
            executionResult=None,
        )

    def _update_meeting_recommendation(
        self,
        meeting: MeetingDetail,
        recommendation: ActionRecommendation,
    ) -> None:
        for i, existing in enumerate(meeting.recentActionRecommendations):
            if existing.id == recommendation.id:
                meeting.recentActionRecommendations[i] = recommendation.model_copy(deep=True)
                break


repository = MeetingStore()


def _keywords_for_memory_template(source_meeting_id: str) -> tuple[str, ...]:
    if "auth" in source_meeting_id:
        return ("auth", "configuration", "release")
    if "migration" in source_meeting_id:
        return ("migration", "staging", "rerun")
    return ("alert", "ownership", "handoff", "incident")
