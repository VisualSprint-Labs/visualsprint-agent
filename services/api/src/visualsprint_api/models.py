"""Pydantic models for the VisualSprint API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


MeetingStatus = Literal["draft", "live", "ended"]
SourceConnectorSlug = Literal[
    "browser_live_capture",
    "recording_upload",
    "document_link",
]
CaptureSessionStatus = Literal["idle", "recording", "completed"]
ChunkProcessingStatus = Literal["registered", "processing", "processed"]
ProcessingSourceMode = Literal["local_fallback", "downstream_service"]
CaptureChunkLifecycleStatus = Literal[
    "registered",
    "upload_ready",
    "uploaded",
    "processing",
    "processed",
]
CaptureChunkUploadStatus = Literal["pending", "ready", "uploaded"]
BlockerSeverity = Literal["low", "medium", "high"]
MemoryMatchStrength = Literal["related", "recurring", "critical"]
MemoryMatchRelation = Literal["new", "recurring", "reopened", "resolved_previously"]
ReasoningRecordStatus = Literal["open", "updated", "resolved", "reopened"]
ReasoningRecordType = Literal["decision", "commitment", "blocker", "open_question"]
ScreenEventKind = Literal[
    "code_editor",
    "terminal",
    "diagram",
    "slide",
    "error",
    "ui_state",
]
LiveEventKind = Literal[
    "system",
    "capture",
    "transcript",
    "decision",
    "commitment",
    "blocker",
    "memory",
]
DownstreamServiceKind = Literal["control_plane", "agents", "ingest", "media"]
DownstreamServiceConnectionStatus = Literal["ok", "unreachable", "not_configured"]
ActionRecommendationType = Literal[
    "jira_create_issue",
    "jira_update_issue",
    "jira_resolve_issue",
    "slack_post_summary",
    "slack_broadcast_decision",
    "slack_alert_blocker",
    "slack_remind_commitment",
    "slack_notify_resolution",
]
JiraIssueType = Literal["task", "story", "bug"]
JiraAction = Literal["create_issue", "update_issue", "resolve_issue"]
SlackActionType = Literal[
    "post_summary",
    "broadcast_decision",
    "alert_blocker",
    "remind_commitment",
    "notify_resolution",
]
ActionRecommendationStatus = Literal[
    "pending",
    "approved",
    "rejected",
    "executed",
    "failed",
]
ActionUrgency = Literal["critical", "high", "medium", "low"]
ActionConfidenceLevel = Literal["low", "medium", "high"]


class MeetingMetrics(BaseModel):
    decisionsCount: int = 0
    commitmentsCount: int = 0
    blockersCount: int = 0
    memoryMatchesCount: int = 0
    openQuestionsCount: int = 0
    transcriptSegmentsCount: int = 0
    visualEventsCount: int = 0
    captureEventsCount: int = 0
    captureChunksCount: int = 0
    capturedBytes: int = 0
    actionRecommendationsCount: int = 0


class DownstreamServiceStatus(BaseModel):
    service: str
    kind: DownstreamServiceKind
    configured: bool
    reachable: bool
    mode: Literal["local", "remote", "fallback"]
    baseUrl: str | None = None
    status: DownstreamServiceConnectionStatus
    version: str | None = None
    track: str | None = None
    note: str = Field(min_length=4, max_length=240)


class ElasticIntegrationStatus(BaseModel):
    provider: Literal["elastic"] = "elastic"
    writebackConfigured: bool
    elasticsearchUrlConfigured: bool
    apiKeySecretConfigured: bool
    mcpServerConfigured: bool
    outcomesIndex: str | None = Field(default=None, min_length=1, max_length=180)
    note: str = Field(min_length=4, max_length=240)


class PlatformMetaResponse(BaseModel):
    service: str
    environment: str
    selectedTrack: str
    supportedTracks: list[str]
    architecture: dict[str, str]
    modules: list[str]
    memoryIntegration: ElasticIntegrationStatus
    downstreamServices: list[DownstreamServiceStatus] = Field(default_factory=list)


class AgentInvocationAuditEntry(BaseModel):
    invokedAt: datetime
    agentKind: Literal["reasoning", "summary"]
    executionMode: Literal[
        "mock",
        "bridge",
        "bridge_fallback",
        "vertex_ai",
        "vertex_ai_fallback",
    ]
    status: Literal["success", "fallback", "error"]
    targetAgentId: str | None = None
    requestKey: str = Field(min_length=4, max_length=160)
    detail: str = Field(min_length=4, max_length=240)


class AgentInvocationAuditSummary(BaseModel):
    available: bool
    source: Literal["agents_service", "local_unavailable"]
    total: int = 0
    reasoningRuns: int = 0
    summaryRuns: int = 0
    bridgeRuns: int = 0
    bridgeFallbackRuns: int = 0
    mockRuns: int = 0
    note: str = Field(min_length=4, max_length=240)


class AgentInvocationAuditResponse(BaseModel):
    summary: AgentInvocationAuditSummary
    invocations: list[AgentInvocationAuditEntry] = Field(default_factory=list)


class AgentSmokeReasoningResult(BaseModel):
    attempted: bool
    selectedChunkId: str | None = None
    source: ProcessingSourceMode
    producedOutput: bool
    decisionCount: int = 0
    commitmentCount: int = 0
    blockerCount: int = 0
    openQuestionCount: int = 0
    memoryMatchCount: int = 0
    note: str = Field(min_length=4, max_length=240)


class AgentSmokeSummaryResult(BaseModel):
    attempted: bool
    source: ProcessingSourceMode
    producedOutput: bool
    executiveSummaryLength: int = 0
    note: str = Field(min_length=4, max_length=240)


class AgentSmokeResponse(BaseModel):
    meetingId: str
    reasoning: AgentSmokeReasoningResult
    summary: AgentSmokeSummaryResult


class CaptureChunkUploadTarget(BaseModel):
    method: Literal["PUT"] = "PUT"
    objectPath: str = Field(min_length=8, max_length=240)
    signedUrl: str | None = None
    requiredHeaders: dict[str, str] = Field(default_factory=dict)
    expiresAt: datetime | None = None


class CaptureChunkSummary(BaseModel):
    id: str
    clientChunkId: str = Field(min_length=8, max_length=120)
    sequence: int = Field(ge=1)
    recordedAt: datetime
    durationMs: int = Field(ge=250)
    byteSize: int = Field(ge=0)
    mimeType: str = Field(min_length=3, max_length=120)
    lifecycleStatus: CaptureChunkLifecycleStatus
    uploadStatus: CaptureChunkUploadStatus
    storageObjectPath: str = Field(min_length=8, max_length=240)
    uploadTarget: CaptureChunkUploadTarget
    processingStatus: ChunkProcessingStatus
    frameCount: int = Field(default=0, ge=0)
    transcriptSegmentCount: int = 0
    visualEventCount: int = 0
    signalCount: int = 0
    transcriptSource: ProcessingSourceMode = "local_fallback"
    mediaSource: ProcessingSourceMode = "local_fallback"
    reasoningSource: ProcessingSourceMode = "local_fallback"


class CaptureSessionSummary(BaseModel):
    id: str
    status: CaptureSessionStatus
    sourceConnector: SourceConnectorSlug
    recorderMimeType: str = Field(min_length=3, max_length=120)
    hasDisplayVideo: bool
    hasDisplayAudio: bool
    hasMicrophoneAudio: bool
    displaySurface: str = Field(default="unknown", min_length=2, max_length=20)
    startedAt: datetime
    endedAt: datetime | None = None
    chunkCount: int = 0
    totalBytes: int = 0


class LiveEvent(BaseModel):
    id: str
    kind: LiveEventKind
    at: datetime
    title: str
    detail: str


class TranscriptSegment(BaseModel):
    id: str
    speakerLabel: str = Field(min_length=2, max_length=60)
    startedAt: datetime
    endedAt: datetime
    text: str = Field(min_length=8, max_length=500)


class ScreenEvent(BaseModel):
    id: str
    kind: ScreenEventKind
    summary: str = Field(min_length=6, max_length=220)
    frameTimestampMs: int = Field(ge=0)
    recordedAt: datetime


class EvidenceReference(BaseModel):
    chunkId: str = Field(min_length=4, max_length=120)
    clientChunkId: str = Field(min_length=8, max_length=120)
    tStartMs: int = Field(ge=0)
    tEndMs: int = Field(ge=0)
    transcriptRef: str | None = Field(default=None, min_length=4, max_length=120)
    frameRef: str | None = Field(default=None, min_length=4, max_length=120)
    note: str = Field(min_length=6, max_length=220)


class DecisionRecord(BaseModel):
    id: str
    title: str = Field(min_length=4, max_length=180)
    rationale: str = Field(min_length=8, max_length=500)
    speakerLabel: str = Field(min_length=2, max_length=60)
    status: ReasoningRecordStatus
    firstSeenChunkId: str = Field(min_length=8, max_length=120)
    lastUpdatedChunkId: str = Field(min_length=8, max_length=120)
    recordedAt: datetime
    evidence: list[EvidenceReference] = Field(default_factory=list, max_length=4)


class CommitmentRecord(BaseModel):
    id: str
    ownerLabel: str = Field(min_length=2, max_length=60)
    action: str = Field(min_length=6, max_length=220)
    dueHint: str = Field(min_length=2, max_length=60)
    status: ReasoningRecordStatus
    firstSeenChunkId: str = Field(min_length=8, max_length=120)
    lastUpdatedChunkId: str = Field(min_length=8, max_length=120)
    recordedAt: datetime
    evidence: list[EvidenceReference] = Field(default_factory=list, max_length=4)


class BlockerRecord(BaseModel):
    id: str
    summary: str = Field(min_length=6, max_length=220)
    severity: BlockerSeverity
    ownerLabel: str = Field(min_length=2, max_length=60)
    status: ReasoningRecordStatus
    firstSeenChunkId: str = Field(min_length=8, max_length=120)
    lastUpdatedChunkId: str = Field(min_length=8, max_length=120)
    recordedAt: datetime
    evidence: list[EvidenceReference] = Field(default_factory=list, max_length=4)


class MemoryMatch(BaseModel):
    id: str
    sourceMeetingId: str = Field(min_length=4, max_length=120)
    summary: str = Field(min_length=6, max_length=240)
    sourceMeetingTitle: str = Field(min_length=3, max_length=120)
    strength: MemoryMatchStrength
    relation: MemoryMatchRelation
    score: float = Field(ge=0.0, le=1.0)
    snippet: str = Field(min_length=6, max_length=320)
    recordedAt: datetime


class OpenQuestionRecord(BaseModel):
    id: str
    question: str = Field(min_length=8, max_length=240)
    speakerLabel: str = Field(min_length=2, max_length=60)
    status: ReasoningRecordStatus
    firstSeenChunkId: str = Field(min_length=8, max_length=120)
    lastUpdatedChunkId: str = Field(min_length=8, max_length=120)
    recordedAt: datetime
    evidence: list[EvidenceReference] = Field(default_factory=list, max_length=4)


class MeetingSummary(BaseModel):
    id: str
    title: str = Field(min_length=3, max_length=120)
    participantCount: int = Field(ge=1, le=50)
    status: MeetingStatus
    sourceConnector: SourceConnectorSlug
    primaryTrack: str
    createdAt: datetime
    startedAt: datetime | None = None
    endedAt: datetime | None = None
    notes: str = Field(default="", max_length=500)
    metrics: MeetingMetrics


class JiraRecommendation(BaseModel):
    action: JiraAction
    issueType: JiraIssueType
    title: str = Field(min_length=4, max_length=180)
    description: str = Field(min_length=8, max_length=600)
    priority: Literal["lowest", "low", "medium", "high", "highest"] = "medium"
    ownerLabel: str = Field(default="not mentioned", min_length=2, max_length=60)
    evidence: list[EvidenceReference] = Field(default_factory=list, max_length=4)
    confidence: float = Field(ge=0.0, le=1.0)


class SlackRecommendation(BaseModel):
    type: SlackActionType
    channel: str = Field(default="not specified", min_length=2, max_length=120)
    title: str = Field(min_length=4, max_length=180)
    message: str = Field(min_length=8, max_length=800)
    evidence: list[EvidenceReference] = Field(default_factory=list, max_length=4)
    confidence: float = Field(ge=0.0, le=1.0)


class ActionRecommendation(BaseModel):
    id: str
    meetingId: str
    type: ActionRecommendationType
    status: ActionRecommendationStatus
    urgency: ActionUrgency
    confidence: float = Field(ge=0.0, le=1.0)
    jiraDetails: JiraRecommendation | None = None
    slackDetails: SlackRecommendation | None = None
    evidence: list[EvidenceReference] = Field(default_factory=list, max_length=4)
    createdAt: datetime
    updatedAt: datetime
    executedAt: datetime | None = None
    executionResult: str | None = Field(default=None, max_length=500)


class ActionRecommendationInput(BaseModel):
    type: ActionRecommendationType
    urgency: ActionUrgency
    confidence: float = Field(ge=0.0, le=1.0)
    jiraDetails: JiraRecommendation | None = None
    slackDetails: SlackRecommendation | None = None
    evidence: list[EvidenceReference] = Field(default_factory=list, max_length=4)


class ActionApprovalRequest(BaseModel):
    approved: bool
    note: str = Field(default="", max_length=240)


class ActionExecutionResult(BaseModel):
    recommendationId: str
    status: Literal["executed", "failed"]
    detail: str = Field(min_length=4, max_length=500)
    executedAt: datetime


class ActionRecommendationsResponse(BaseModel):
    recommendations: list[ActionRecommendation] = Field(default_factory=list)


class ActionRecommendationResponse(BaseModel):
    recommendation: ActionRecommendation


class MeetingDetail(MeetingSummary):
    latestEvents: list[LiveEvent] = Field(default_factory=list)
    activeCaptureSession: CaptureSessionSummary | None = None
    recentCaptureChunks: list[CaptureChunkSummary] = Field(default_factory=list)
    recentTranscriptSegments: list[TranscriptSegment] = Field(default_factory=list)
    recentScreenEvents: list[ScreenEvent] = Field(default_factory=list)
    recentDecisions: list[DecisionRecord] = Field(default_factory=list)
    recentCommitments: list[CommitmentRecord] = Field(default_factory=list)
    recentBlockers: list[BlockerRecord] = Field(default_factory=list)
    recentMemoryMatches: list[MemoryMatch] = Field(default_factory=list)
    recentOpenQuestions: list[OpenQuestionRecord] = Field(default_factory=list)
    recentActionRecommendations: list[ActionRecommendation] = Field(default_factory=list)


class CreateMeetingRequest(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    participantCount: int = Field(ge=1, le=50)
    sourceConnector: SourceConnectorSlug
    notes: str = Field(default="", max_length=500)


class StartCaptureSessionRequest(BaseModel):
    recorderMimeType: str | None = Field(default=None, min_length=3, max_length=120)
    hasDisplayVideo: bool = True
    hasDisplayAudio: bool = False
    hasMicrophoneAudio: bool = False
    displaySurface: str = Field(default="unknown", min_length=2, max_length=20)


class RegisterCaptureChunkRequest(BaseModel):
    clientChunkId: str = Field(min_length=8, max_length=120)
    sequence: int = Field(ge=1)
    durationMs: int = Field(ge=250, le=120_000)
    byteSize: int = Field(ge=0)
    mimeType: str = Field(min_length=3, max_length=120)


class CompleteCaptureChunkUploadRequest(BaseModel):
    clientChunkId: str = Field(min_length=8, max_length=120)
    # Base64-encoded captured media for this chunk (short webm clip or still frame).
    # When present and vision is configured, the backend runs a real Gemini
    # multimodal pass instead of the deterministic screen/transcript stubs.
    mediaBase64: str | None = Field(default=None, max_length=20_000_000)
    mediaMimeType: str | None = Field(default=None, max_length=120)


class MeetingListResponse(BaseModel):
    meetings: list[MeetingSummary]


class MeetingDetailResponse(BaseModel):
    meeting: MeetingDetail


class CreateMeetingResponse(BaseModel):
    meeting: MeetingDetail


class CaptureSessionResponse(BaseModel):
    meeting: MeetingDetail
    captureSession: CaptureSessionSummary


class RegisterCaptureChunkResponse(CaptureSessionResponse):
    chunk: CaptureChunkSummary


class CompleteCaptureChunkUploadResponse(CaptureSessionResponse):
    chunk: CaptureChunkSummary


class MeetingStateSnapshot(BaseModel):
    meetingId: str
    meetingStatus: MeetingStatus
    activeCaptureSessionId: str | None = None
    latestChunkClientId: str | None = None
    openDecisions: list[DecisionRecord] = Field(default_factory=list)
    openCommitments: list[CommitmentRecord] = Field(default_factory=list)
    openBlockers: list[BlockerRecord] = Field(default_factory=list)
    openQuestions: list[OpenQuestionRecord] = Field(default_factory=list)


class MeetingStateResponse(BaseModel):
    meetingState: MeetingStateSnapshot


class ChunkContext(BaseModel):
    chunk: CaptureChunkSummary
    transcriptSegments: list[TranscriptSegment] = Field(default_factory=list)
    screenEvents: list[ScreenEvent] = Field(default_factory=list)


class ChunkContextResponse(BaseModel):
    meetingId: str
    meetingState: MeetingStateSnapshot
    chunkContext: ChunkContext


class ChunkInsightFocus(BaseModel):
    recordType: ReasoningRecordType
    summary: str = Field(min_length=6, max_length=240)
    detail: str = Field(min_length=8, max_length=500)
    evidence: list[str] = Field(default_factory=list, max_length=6)


class ChunkInsight(BaseModel):
    meetingId: str
    meetingTitle: str = Field(min_length=3, max_length=120)
    meetingNotes: str = Field(default="", max_length=500)
    clientChunkId: str = Field(min_length=8, max_length=120)
    focusSummary: str = Field(min_length=12, max_length=400)
    attentionFlags: list[str] = Field(default_factory=list, max_length=6)
    reasoningChecklist: list[str] = Field(default_factory=list, max_length=8)
    focusAreas: list[ChunkInsightFocus] = Field(default_factory=list, max_length=6)
    memoryQueries: list["SearchPriorOutcomesRequest"] = Field(default_factory=list, max_length=6)
    memoryMatches: list[MemoryMatch] = Field(default_factory=list, max_length=6)
    transcriptSegments: list[TranscriptSegment] = Field(default_factory=list)
    screenEvents: list[ScreenEvent] = Field(default_factory=list)
    meetingState: MeetingStateSnapshot
    chunkContext: ChunkContext


class ChunkInsightResponse(BaseModel):
    insight: ChunkInsight


class SummaryPacketHighlight(BaseModel):
    title: str = Field(min_length=4, max_length=180)
    detail: str = Field(min_length=6, max_length=320)
    kind: LiveEventKind
    recordedAt: datetime


class MeetingSummaryPacket(BaseModel):
    meetingId: str
    meetingTitle: str = Field(min_length=3, max_length=120)
    meetingStatus: MeetingStatus
    draftExecutiveSummary: str = Field(min_length=12, max_length=600)
    reportChecklist: list[str] = Field(default_factory=list, max_length=8)
    timelineHighlights: list[SummaryPacketHighlight] = Field(default_factory=list, max_length=8)
    meetingState: MeetingStateSnapshot
    decisions: list[DecisionRecord] = Field(default_factory=list)
    commitments: list[CommitmentRecord] = Field(default_factory=list)
    blockers: list[BlockerRecord] = Field(default_factory=list)
    openQuestions: list[OpenQuestionRecord] = Field(default_factory=list)
    memoryHighlights: list[MemoryMatch] = Field(default_factory=list)
    transcriptEvidence: list[TranscriptSegment] = Field(default_factory=list)
    visualEvidence: list[ScreenEvent] = Field(default_factory=list)


class MeetingSummaryPacketResponse(BaseModel):
    summaryPacket: MeetingSummaryPacket


class SearchPriorOutcomesRequest(BaseModel):
    recordType: ReasoningRecordType
    summary: str = Field(min_length=6, max_length=240)
    detail: str = Field(min_length=6, max_length=500)


class SearchPriorOutcomesResponse(BaseModel):
    matches: list[MemoryMatch]


class OutcomeSearchResult(BaseModel):
    recordType: ReasoningRecordType
    summary: str
    detail: str
    status: ReasoningRecordStatus
    meetingId: str
    meetingTitle: str
    ownerLabel: str | None = None
    speakerLabel: str | None = None
    dueHint: str | None = None
    severity: BlockerSeverity | None = None
    updatedAt: datetime
    score: float


class OutcomeSearchResponse(BaseModel):
    query: str
    recordType: ReasoningRecordType | None = None
    available: bool
    total: int
    results: list[OutcomeSearchResult]


class IndexedOutcomeDocument(BaseModel):
    id: str
    meetingId: str
    recordType: ReasoningRecordType
    summary: str = Field(min_length=4, max_length=240)
    detail: str = Field(min_length=6, max_length=600)
    status: ReasoningRecordStatus
    ownerLabel: str | None = Field(default=None, min_length=2, max_length=60)
    speakerLabel: str | None = Field(default=None, min_length=2, max_length=60)
    dueHint: str | None = Field(default=None, min_length=2, max_length=60)
    severity: BlockerSeverity | None = None
    firstSeenChunkId: str = Field(min_length=8, max_length=120)
    lastUpdatedChunkId: str = Field(min_length=8, max_length=120)
    createdAt: datetime
    updatedAt: datetime
    evidence: list[EvidenceReference] = Field(default_factory=list, max_length=4)


class IndexedOutcomeDocumentsResponse(BaseModel):
    documents: list[IndexedOutcomeDocument] = Field(default_factory=list)


ChunkInsight.model_rebuild()
ChunkInsightResponse.model_rebuild()
MeetingSummaryPacket.model_rebuild()
MeetingSummaryPacketResponse.model_rebuild()


class MeetingStreamEvent(BaseModel):
    type: Literal["meeting.updated"] = "meeting.updated"
    revision: int = Field(ge=0)
    meeting: MeetingDetail


class FinalReport(BaseModel):
    meetingId: str
    generatedAt: datetime
    executiveSummary: str = Field(min_length=12, max_length=600)
    summarySource: ProcessingSourceMode = "local_fallback"
    decisions: list[DecisionRecord] = Field(default_factory=list)
    commitments: list[CommitmentRecord] = Field(default_factory=list)
    blockers: list[BlockerRecord] = Field(default_factory=list)
    openQuestions: list[OpenQuestionRecord] = Field(default_factory=list)
    memoryHighlights: list[MemoryMatch] = Field(default_factory=list)


class FinalReportResponse(BaseModel):
    report: FinalReport


class AgentDecisionInput(BaseModel):
    title: str = Field(min_length=4, max_length=180)
    rationale: str = Field(min_length=8, max_length=500)
    speakerLabel: str = Field(min_length=2, max_length=60)


class AgentCommitmentInput(BaseModel):
    ownerLabel: str = Field(min_length=2, max_length=60)
    action: str = Field(min_length=6, max_length=220)
    dueHint: str = Field(min_length=2, max_length=60)


class AgentBlockerInput(BaseModel):
    summary: str = Field(min_length=6, max_length=220)
    severity: BlockerSeverity
    ownerLabel: str = Field(min_length=2, max_length=60)


class AgentOpenQuestionInput(BaseModel):
    question: str = Field(min_length=8, max_length=240)
    speakerLabel: str = Field(min_length=2, max_length=60)


class AgentMemoryMatchInput(BaseModel):
    sourceMeetingId: str = Field(min_length=4, max_length=120)
    summary: str = Field(min_length=6, max_length=240)
    sourceMeetingTitle: str = Field(min_length=3, max_length=120)
    strength: MemoryMatchStrength
    relation: MemoryMatchRelation
    score: float = Field(ge=0.0, le=1.0)
    snippet: str = Field(min_length=6, max_length=320)


class RegisterAgentOutputsRequest(BaseModel):
    clientChunkId: str = Field(min_length=8, max_length=120)
    decisions: list[AgentDecisionInput] = Field(default_factory=list)
    commitments: list[AgentCommitmentInput] = Field(default_factory=list)
    blockers: list[AgentBlockerInput] = Field(default_factory=list)
    openQuestions: list[AgentOpenQuestionInput] = Field(default_factory=list)
    memoryMatches: list[AgentMemoryMatchInput] = Field(default_factory=list)
    resolvedDecisionIds: list[str] = Field(default_factory=list, max_length=12)
    resolvedCommitmentIds: list[str] = Field(default_factory=list, max_length=12)
    resolvedBlockerIds: list[str] = Field(default_factory=list, max_length=12)
    resolvedOpenQuestionIds: list[str] = Field(default_factory=list, max_length=12)


class RegisterAgentOutputsResponse(BaseModel):
    meeting: MeetingDetail
    meetingState: MeetingStateSnapshot
