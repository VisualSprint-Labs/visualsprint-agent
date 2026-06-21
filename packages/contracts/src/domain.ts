export type PartnerTrackSlug =
  | "arize"
  | "elastic"
  | "fivetran"
  | "gitlab"
  | "mongodb"
  | "dynatrace";

export type PlatformCapabilityType = "deterministic" | "intelligence" | "platform";
export type MeetingStatus = "draft" | "live" | "ended";
export type SourceConnectorSlug =
  | "browser_live_capture"
  | "recording_upload"
  | "document_link";
export type LiveEventKind =
  | "system"
  | "capture"
  | "transcript"
  | "decision"
  | "commitment"
  | "blocker"
  | "memory";
export type CaptureSessionStatus = "idle" | "recording" | "completed";
export type ChunkProcessingStatus = "registered" | "processing" | "processed";
export type ProcessingSourceMode = "local_fallback" | "downstream_service";
export type CaptureChunkLifecycleStatus =
  | "registered"
  | "upload_ready"
  | "uploaded"
  | "processing"
  | "processed";
export type CaptureChunkUploadStatus = "pending" | "ready" | "uploaded";
export type BlockerSeverity = "low" | "medium" | "high";
export type MemoryMatchStrength = "related" | "recurring" | "critical";
export type MemoryMatchRelation =
  | "new"
  | "recurring"
  | "reopened"
  | "resolved_previously";
export type ReasoningRecordStatus = "open" | "updated" | "resolved" | "reopened";
export type ReasoningRecordType =
  | "decision"
  | "commitment"
  | "blocker"
  | "open_question";
export type ScreenEventKind =
  | "code_editor"
  | "terminal"
  | "diagram"
  | "slide"
  | "error"
  | "ui_state";

export type ActionRecommendationType =
  | "jira_create_issue"
  | "jira_update_issue"
  | "jira_resolve_issue"
  | "slack_post_summary"
  | "slack_broadcast_decision"
  | "slack_alert_blocker"
  | "slack_remind_commitment"
  | "slack_notify_resolution";

export type JiraIssueType = "task" | "story" | "bug";

export type JiraAction = "create_issue" | "update_issue" | "resolve_issue";

export type SlackActionType =
  | "post_summary"
  | "broadcast_decision"
  | "alert_blocker"
  | "remind_commitment"
  | "notify_resolution";

export type ActionRecommendationStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "executed"
  | "failed";

export type ActionUrgency = "critical" | "high" | "medium" | "low";

export type ActionConfidenceLevel = "low" | "medium" | "high";

export interface PartnerTrack {
  slug: PartnerTrackSlug;
  label: string;
}

export interface PlatformCapability {
  id: string;
  label: string;
  description: string;
  type: PlatformCapabilityType;
}

export interface DashboardModule {
  id: string;
  label: string;
  description: string;
}

export interface FoundationalService {
  name: string;
  responsibility: string;
}

export interface DownstreamServiceStatus {
  service: string;
  kind: "control_plane" | "agents" | "ingest" | "media";
  configured: boolean;
  reachable: boolean;
  mode: "local" | "remote" | "fallback";
  baseUrl: null | string;
  status: "ok" | "unreachable" | "not_configured";
  version: null | string;
  track: null | string;
  note: string;
}

export interface ElasticIntegrationStatus {
  provider: "elastic";
  writebackConfigured: boolean;
  elasticsearchUrlConfigured: boolean;
  apiKeySecretConfigured: boolean;
  mcpServerConfigured: boolean;
  outcomesIndex: null | string;
  note: string;
}

export interface PlatformMetaResponse {
  service: string;
  environment: string;
  selectedTrack: string;
  supportedTracks: string[];
  architecture: {
    frontend: string;
    backend: string;
    agentOrchestration: string;
    memoryLayer: string;
  };
  modules: string[];
  memoryIntegration: ElasticIntegrationStatus;
  downstreamServices: DownstreamServiceStatus[];
}

export interface AgentInvocationAuditEntry {
  invokedAt: string;
  agentKind: "reasoning" | "summary";
  executionMode:
    | "mock"
    | "bridge"
    | "bridge_fallback"
    | "vertex_ai"
    | "vertex_ai_fallback";
  status: "success" | "fallback" | "error";
  targetAgentId: null | string;
  requestKey: string;
  detail: string;
}

export interface AgentInvocationAuditSummary {
  available: boolean;
  source: "agents_service" | "local_unavailable";
  total: number;
  reasoningRuns: number;
  summaryRuns: number;
  bridgeRuns: number;
  bridgeFallbackRuns: number;
  mockRuns: number;
  note: string;
}

export interface AgentInvocationAuditResponse {
  summary: AgentInvocationAuditSummary;
  invocations: AgentInvocationAuditEntry[];
}

export interface AgentSmokeReasoningResult {
  attempted: boolean;
  selectedChunkId: null | string;
  source: "local_fallback" | "downstream_service";
  producedOutput: boolean;
  decisionCount: number;
  commitmentCount: number;
  blockerCount: number;
  openQuestionCount: number;
  memoryMatchCount: number;
  note: string;
}

export interface AgentSmokeSummaryResult {
  attempted: boolean;
  source: "local_fallback" | "downstream_service";
  producedOutput: boolean;
  executiveSummaryLength: number;
  note: string;
}

export interface AgentSmokeResponse {
  meetingId: string;
  reasoning: AgentSmokeReasoningResult;
  summary: AgentSmokeSummaryResult;
}

export interface MeetingMetrics {
  decisionsCount: number;
  commitmentsCount: number;
  blockersCount: number;
  memoryMatchesCount: number;
  openQuestionsCount: number;
  transcriptSegmentsCount: number;
  visualEventsCount: number;
  captureEventsCount: number;
  captureChunksCount: number;
  capturedBytes: number;
  actionRecommendationsCount: number;
}

export interface CaptureChunkUploadTarget {
  method: "PUT";
  objectPath: string;
  signedUrl: null | string;
  requiredHeaders: Record<string, string>;
  expiresAt: null | string;
}

export interface CaptureChunkSummary {
  id: string;
  clientChunkId: string;
  sequence: number;
  recordedAt: string;
  durationMs: number;
  byteSize: number;
  mimeType: string;
  lifecycleStatus: CaptureChunkLifecycleStatus;
  uploadStatus: CaptureChunkUploadStatus;
  storageObjectPath: string;
  uploadTarget: CaptureChunkUploadTarget;
  processingStatus: ChunkProcessingStatus;
  frameCount: number;
  transcriptSegmentCount: number;
  visualEventCount: number;
  signalCount: number;
  transcriptSource: ProcessingSourceMode;
  mediaSource: ProcessingSourceMode;
  reasoningSource: ProcessingSourceMode;
}

export interface CaptureSessionSummary {
  id: string;
  status: CaptureSessionStatus;
  sourceConnector: SourceConnectorSlug;
  recorderMimeType: string;
  hasDisplayVideo: boolean;
  hasDisplayAudio: boolean;
  hasMicrophoneAudio: boolean;
  startedAt: string;
  endedAt: null | string;
  chunkCount: number;
  totalBytes: number;
}

export interface MeetingSummary {
  id: string;
  title: string;
  participantCount: number;
  status: MeetingStatus;
  sourceConnector: SourceConnectorSlug;
  primaryTrack: PartnerTrackSlug;
  createdAt: string;
  startedAt: null | string;
  endedAt: null | string;
  notes: string;
  metrics: MeetingMetrics;
}

export interface LiveEvent {
  id: string;
  kind: LiveEventKind;
  at: string;
  title: string;
  detail: string;
}

export interface TranscriptSegment {
  id: string;
  speakerLabel: string;
  startedAt: string;
  endedAt: string;
  text: string;
}

export interface ScreenEvent {
  id: string;
  kind: ScreenEventKind;
  summary: string;
  frameTimestampMs: number;
  recordedAt: string;
}

export interface EvidenceReference {
  chunkId: string;
  clientChunkId: string;
  tStartMs: number;
  tEndMs: number;
  transcriptRef: null | string;
  frameRef: null | string;
  note: string;
}

export interface DecisionRecord {
  id: string;
  title: string;
  rationale: string;
  speakerLabel: string;
  status: ReasoningRecordStatus;
  firstSeenChunkId: string;
  lastUpdatedChunkId: string;
  recordedAt: string;
  evidence: EvidenceReference[];
}

export interface CommitmentRecord {
  id: string;
  ownerLabel: string;
  action: string;
  dueHint: string;
  status: ReasoningRecordStatus;
  firstSeenChunkId: string;
  lastUpdatedChunkId: string;
  recordedAt: string;
  evidence: EvidenceReference[];
}

export interface BlockerRecord {
  id: string;
  summary: string;
  severity: BlockerSeverity;
  ownerLabel: string;
  status: ReasoningRecordStatus;
  firstSeenChunkId: string;
  lastUpdatedChunkId: string;
  recordedAt: string;
  evidence: EvidenceReference[];
}

export interface MemoryMatch {
  id: string;
  sourceMeetingId: string;
  summary: string;
  sourceMeetingTitle: string;
  strength: MemoryMatchStrength;
  relation: MemoryMatchRelation;
  score: number;
  snippet: string;
  recordedAt: string;
}

export interface OpenQuestionRecord {
  id: string;
  question: string;
  speakerLabel: string;
  status: ReasoningRecordStatus;
  firstSeenChunkId: string;
  lastUpdatedChunkId: string;
  recordedAt: string;
  evidence: EvidenceReference[];
}

export interface MeetingDetail extends MeetingSummary {
  latestEvents: LiveEvent[];
  activeCaptureSession: null | CaptureSessionSummary;
  recentCaptureChunks: CaptureChunkSummary[];
  recentTranscriptSegments: TranscriptSegment[];
  recentScreenEvents: ScreenEvent[];
  recentDecisions: DecisionRecord[];
  recentCommitments: CommitmentRecord[];
  recentBlockers: BlockerRecord[];
  recentMemoryMatches: MemoryMatch[];
  recentOpenQuestions: OpenQuestionRecord[];
  recentActionRecommendations: ActionRecommendation[];
}

export interface CreateMeetingRequest {
  title: string;
  participantCount: number;
  sourceConnector: SourceConnectorSlug;
  notes: string;
}

export interface CreateMeetingResponse {
  meeting: MeetingDetail;
}

export interface MeetingListResponse {
  meetings: MeetingSummary[];
}

export interface MeetingDetailResponse {
  meeting: MeetingDetail;
}

export interface StartCaptureSessionRequest {
  recorderMimeType: null | string;
  hasDisplayVideo: boolean;
  hasDisplayAudio: boolean;
  hasMicrophoneAudio: boolean;
}

export interface RegisterCaptureChunkRequest {
  clientChunkId: string;
  sequence: number;
  durationMs: number;
  byteSize: number;
  mimeType: string;
}

export interface CompleteCaptureChunkUploadRequest {
  clientChunkId: string;
  /** Base64-encoded captured media (short webm clip) for real multimodal vision. */
  mediaBase64?: string | null;
  mediaMimeType?: string | null;
}

export interface CaptureSessionResponse {
  meeting: MeetingDetail;
  captureSession: CaptureSessionSummary;
}

export interface RegisterCaptureChunkResponse extends CaptureSessionResponse {
  chunk: CaptureChunkSummary;
}

export interface CompleteCaptureChunkUploadResponse extends CaptureSessionResponse {
  chunk: CaptureChunkSummary;
}

export interface MeetingStateSnapshot {
  meetingId: string;
  meetingStatus: MeetingStatus;
  activeCaptureSessionId: null | string;
  latestChunkClientId: null | string;
  openDecisions: DecisionRecord[];
  openCommitments: CommitmentRecord[];
  openBlockers: BlockerRecord[];
  openQuestions: OpenQuestionRecord[];
}

export interface MeetingStateResponse {
  meetingState: MeetingStateSnapshot;
}

export interface ChunkContext {
  chunk: CaptureChunkSummary;
  transcriptSegments: TranscriptSegment[];
  screenEvents: ScreenEvent[];
}

export interface ChunkContextResponse {
  meetingId: string;
  meetingState: MeetingStateSnapshot;
  chunkContext: ChunkContext;
}

export interface ChunkInsightFocus {
  recordType: ReasoningRecordType;
  summary: string;
  detail: string;
  evidence: string[];
}

export interface ChunkInsight {
  meetingId: string;
  meetingTitle: string;
  meetingNotes: string;
  clientChunkId: string;
  focusSummary: string;
  attentionFlags: string[];
  reasoningChecklist: string[];
  focusAreas: ChunkInsightFocus[];
  memoryQueries: SearchPriorOutcomesRequest[];
  meetingState: MeetingStateSnapshot;
  chunkContext: ChunkContext;
}

export interface ChunkInsightResponse {
  insight: ChunkInsight;
}

export interface SummaryPacketHighlight {
  title: string;
  detail: string;
  kind: LiveEventKind;
  recordedAt: string;
}

export interface MeetingSummaryPacket {
  meetingId: string;
  meetingTitle: string;
  meetingStatus: MeetingStatus;
  draftExecutiveSummary: string;
  reportChecklist: string[];
  timelineHighlights: SummaryPacketHighlight[];
  meetingState: MeetingStateSnapshot;
  decisions: DecisionRecord[];
  commitments: CommitmentRecord[];
  blockers: BlockerRecord[];
  openQuestions: OpenQuestionRecord[];
  memoryHighlights: MemoryMatch[];
  transcriptEvidence: TranscriptSegment[];
  visualEvidence: ScreenEvent[];
}

export interface MeetingSummaryPacketResponse {
  summaryPacket: MeetingSummaryPacket;
}

export interface SearchPriorOutcomesRequest {
  recordType: ReasoningRecordType;
  summary: string;
  detail: string;
}

export interface SearchPriorOutcomesResponse {
  matches: MemoryMatch[];
}

export interface IndexedOutcomeDocument {
  id: string;
  meetingId: string;
  recordType: ReasoningRecordType;
  summary: string;
  detail: string;
  status: ReasoningRecordStatus;
  ownerLabel: null | string;
  speakerLabel: null | string;
  dueHint: null | string;
  severity: null | BlockerSeverity;
  firstSeenChunkId: string;
  lastUpdatedChunkId: string;
  createdAt: string;
  updatedAt: string;
  evidence: EvidenceReference[];
}

export interface IndexedOutcomeDocumentsResponse {
  documents: IndexedOutcomeDocument[];
}

export interface JiraRecommendation {
  action: JiraAction;
  issueType: JiraIssueType;
  title: string;
  description: string;
  priority: "lowest" | "low" | "medium" | "high" | "highest";
  ownerLabel: string;
  evidence: EvidenceReference[];
  confidence: number;
}

export interface SlackRecommendation {
  type: SlackActionType;
  channel: string;
  title: string;
  message: string;
  evidence: EvidenceReference[];
  confidence: number;
}

export interface ActionRecommendation {
  id: string;
  meetingId: string;
  type: ActionRecommendationType;
  status: ActionRecommendationStatus;
  urgency: ActionUrgency;
  confidence: number;
  jiraDetails: JiraRecommendation | null;
  slackDetails: SlackRecommendation | null;
  evidence: EvidenceReference[];
  createdAt: string;
  updatedAt: string;
  executedAt: string | null;
  executionResult: string | null;
}

export interface ActionRecommendationInput {
  type: ActionRecommendationType;
  urgency: ActionUrgency;
  confidence: number;
  jiraDetails: JiraRecommendation | null;
  slackDetails: SlackRecommendation | null;
  evidence: EvidenceReference[];
}

export interface ActionApprovalRequest {
  approved: boolean;
  note: string;
}

export interface ActionExecutionResult {
  recommendationId: string;
  status: "executed" | "failed";
  detail: string;
  executedAt: string;
}

export interface ActionRecommendationsResponse {
  recommendations: ActionRecommendation[];
}

export interface ActionRecommendationResponse {
  recommendation: ActionRecommendation;
}

export interface MeetingStreamEvent {
  type: "meeting.updated";
  revision: number;
  meeting: MeetingDetail;
}

export interface FinalReport {
  meetingId: string;
  generatedAt: string;
  executiveSummary: string;
  summarySource: ProcessingSourceMode;
  decisions: DecisionRecord[];
  commitments: CommitmentRecord[];
  blockers: BlockerRecord[];
  openQuestions: OpenQuestionRecord[];
  memoryHighlights: MemoryMatch[];
}

export interface FinalReportResponse {
  report: FinalReport;
}

export interface AgentDecisionInput {
  title: string;
  rationale: string;
  speakerLabel: string;
}

export interface AgentCommitmentInput {
  ownerLabel: string;
  action: string;
  dueHint: string;
}

export interface AgentBlockerInput {
  summary: string;
  severity: BlockerSeverity;
  ownerLabel: string;
}

export interface AgentOpenQuestionInput {
  question: string;
  speakerLabel: string;
}

export interface AgentMemoryMatchInput {
  sourceMeetingId: string;
  summary: string;
  sourceMeetingTitle: string;
  strength: MemoryMatchStrength;
  relation: MemoryMatchRelation;
  score: number;
  snippet: string;
}

export interface RegisterAgentOutputsRequest {
  clientChunkId: string;
  decisions: AgentDecisionInput[];
  commitments: AgentCommitmentInput[];
  blockers: AgentBlockerInput[];
  openQuestions: AgentOpenQuestionInput[];
  memoryMatches: AgentMemoryMatchInput[];
  resolvedDecisionIds: string[];
  resolvedCommitmentIds: string[];
  resolvedBlockerIds: string[];
  resolvedOpenQuestionIds: string[];
}

export interface RegisterAgentOutputsResponse {
  meeting: MeetingDetail;
  meetingState: MeetingStateSnapshot;
}

export interface ServiceHealth {
  service: string;
  status: "ok";
  version: string;
  track: PartnerTrackSlug;
}

export const partnerTracks: PartnerTrack[] = [
  { slug: "arize", label: "Arize" },
  { slug: "elastic", label: "Elastic" },
  { slug: "fivetran", label: "Fivetran" },
  { slug: "gitlab", label: "GitLab" },
  { slug: "mongodb", label: "MongoDB" },
  { slug: "dynatrace", label: "Dynatrace" },
];

export const dashboardModules: DashboardModule[] = [
  {
    id: "decisions",
    label: "Decisions with evidence",
    description:
      "Capture the exact conclusion, why it was reached, and which meeting evidence supports it.",
  },
  {
    id: "commitments",
    label: "Commitments and owners",
    description:
      "Assign follow-up work to people and show unresolved promises from prior meetings.",
  },
  {
    id: "blockers",
    label: "Recurring blockers",
    description:
      "Highlight the same problem surfacing across meetings instead of leaving it buried in transcripts.",
  },
  {
    id: "memory",
    label: "Cross-meeting memory",
    description:
      "Use Elastic-backed retrieval to connect new discussion points to organizational history.",
  },
];

export const platformCapabilities: PlatformCapability[] = [
  {
    id: "capture",
    label: "Deterministic capture pipeline",
    description:
      "Signed uploads, chunk lifecycle state, and retry-safe media handling stay in conventional services.",
    type: "deterministic",
  },
  {
    id: "reasoning",
    label: "Managed agent orchestration",
    description:
      "Google Agent Builder remains the orchestration surface for meeting reasoning, memory, and summarization.",
    type: "intelligence",
  },
  {
    id: "contracts",
    label: "Shared domain contracts",
    description:
      "The repo uses common product vocabulary for partner tracks, dashboard surfaces, and service metadata.",
    type: "platform",
  },
  {
    id: "tenancy",
    label: "Future-proof tenancy boundaries",
    description:
      "Tenant-aware data boundaries are part of the architecture even before multi-organization features ship.",
    type: "platform",
  },
];

export const foundationalServices: FoundationalService[] = [
  {
    name: "Web shell",
    responsibility:
      "Hosts the product dashboard, meeting setup flow, and hackathon-aligned platform narrative.",
  },
  {
    name: "API control plane",
    responsibility:
      "Publishes service health, architecture metadata, and the deterministic foundation for later meeting workflows.",
  },
  {
    name: "Contracts package",
    responsibility:
      "Centralizes the language shared by the UI, APIs, and future services before implementation branches out.",
  },
];

export const sourceConnectors: Array<{
  slug: SourceConnectorSlug;
  label: string;
  description: string;
}> = [
  {
    slug: "browser_live_capture",
    label: "Browser live capture",
    description:
      "The first production connector for screen share, microphone, and live meeting session intake.",
  },
  {
    slug: "recording_upload",
    label: "Recording upload",
    description:
      "Future connector for recorded meeting files that should reuse the same downstream pipeline.",
  },
  {
    slug: "document_link",
    label: "Document link",
    description:
      "Future connector for linked docs and structured context that enriches the meeting memory layer.",
  },
];

export const captureStages = [
  {
    id: "meeting",
    label: "Meeting session",
    description: "Create and transition the deterministic meeting lifecycle.",
  },
  {
    id: "capture",
    label: "Capture bootstrap",
    description:
      "Obtain browser permission, start the recorder, and register the capture session with the control plane.",
  },
  {
    id: "chunking",
    label: "Chunk registration",
    description:
      "Emit time-based chunks and keep chunk metadata visible before storage and agent processing are added.",
  },
  {
    id: "processing",
    label: "Mock processing",
    description:
      "Simulate transcript, reasoning, and memory outputs so the live dashboard can evolve before real services are integrated.",
  },
] as const;
