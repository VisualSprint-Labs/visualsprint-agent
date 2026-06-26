import type {
  ActionApprovalRequest,
  ActionExecutionResult,
  ActionRecommendationsResponse,
  ActionRecommendationResponse,
  AgentInvocationAuditResponse,
  AgentSmokeResponse,
  ChunkInsightResponse,
  CompleteCaptureChunkUploadRequest,
  CompleteCaptureChunkUploadResponse,
  CaptureSessionResponse,
  CreateMeetingRequest,
  CreateMeetingResponse,
  FinalReportResponse,
  IndexedOutcomeDocumentsResponse,
  MeetingSummaryPacketResponse,
  PlatformMetaResponse,
  MeetingStreamEvent,
  MeetingDetailResponse,
  MeetingListResponse,
  OutcomeSearchResponse,
  RegisterAgentOutputsRequest,
  RegisterAgentOutputsResponse,
  RegisterCaptureChunkRequest,
  RegisterCaptureChunkResponse,
  StartCaptureSessionRequest,
} from "@visualsprint/contracts";

import { getPublicApiBaseUrl } from "./env";

const defaultApiBaseUrl = getPublicApiBaseUrl();

class ApiError extends Error {
  status: number;

  constructor(status: number, detail: string) {
    super(detail || `Request failed with ${status}`);
    this.name = "ApiError";
    this.status = status;
  }
}

function sleep(ms: number) {
  return new Promise<void>((resolve) => {
    globalThis.setTimeout(resolve, ms);
  });
}

function shouldRetry(method: string, attempt: number, error: unknown) {
  if (method !== "GET" || attempt >= 2) {
    return false;
  }
  if (error instanceof ApiError) {
    return [408, 425, 429, 500, 502, 503, 504].includes(error.status);
  }
  return error instanceof TypeError;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? "GET").toUpperCase();

  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      const response = await fetch(`${defaultApiBaseUrl}${path}`, {
        ...init,
        headers: {
          "Content-Type": "application/json",
          ...(init?.headers ?? {}),
        },
        cache: "no-store",
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new ApiError(response.status, detail);
      }

      return (await response.json()) as T;
    } catch (error) {
      if (!shouldRetry(method, attempt, error)) {
        throw error;
      }
      await sleep(300 * (attempt + 1));
    }
  }

  throw new Error("Request failed after retries.");
}

export function getApiBaseUrl() {
  return defaultApiBaseUrl;
}

export function getMeetingEventsUrl(meetingId: string) {
  return `${defaultApiBaseUrl}/api/meetings/${meetingId}/events`;
}

export function listMeetings() {
  return request<MeetingListResponse>("/api/meetings");
}

export function getPlatformMeta() {
  return request<PlatformMetaResponse>("/api/meta");
}

export function getAgentInvocationAudit() {
  return request<AgentInvocationAuditResponse>("/api/meta/agents/invocations");
}

export function runAgentSmoke(meetingId: string, clientChunkId?: string) {
  const query = clientChunkId
    ? `?clientChunkId=${encodeURIComponent(clientChunkId)}`
    : "";
  return request<AgentSmokeResponse>(`/api/meetings/${meetingId}/agents/smoke${query}`, {
    method: "POST",
  });
}

export function getMeeting(meetingId: string) {
  return request<MeetingDetailResponse>(`/api/meetings/${meetingId}`);
}

export function createMeeting(payload: CreateMeetingRequest) {
  return request<CreateMeetingResponse>("/api/meetings", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function startMeeting(meetingId: string) {
  return request<MeetingDetailResponse>(`/api/meetings/${meetingId}/start`, {
    method: "POST",
  });
}

export function endMeeting(meetingId: string) {
  return request<MeetingDetailResponse>(`/api/meetings/${meetingId}/end`, {
    method: "POST",
  });
}

export function getFinalReport(meetingId: string) {
  return request<FinalReportResponse>(`/api/meetings/${meetingId}/final-report`);
}

export function getChunkInsight(meetingId: string, clientChunkId: string) {
  return request<ChunkInsightResponse>(
    `/api/meetings/${meetingId}/insights/chunks/${clientChunkId}`,
  );
}

export function getSummaryPacket(meetingId: string) {
  return request<MeetingSummaryPacketResponse>(`/api/meetings/${meetingId}/summary-packet`);
}

export function getIndexedOutcomeDocuments(meetingId: string) {
  return request<IndexedOutcomeDocumentsResponse>(
    `/api/meetings/${meetingId}/memory/index-documents`,
  );
}

export function finalizeReport(meetingId: string) {
  return request<FinalReportResponse>(`/api/meetings/${meetingId}/final-report`, {
    method: "POST",
  });
}

export function registerAgentOutputs(
  meetingId: string,
  payload: RegisterAgentOutputsRequest,
) {
  return request<RegisterAgentOutputsResponse>(`/api/meetings/${meetingId}/outputs/register`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function startCaptureSession(
  meetingId: string,
  payload: StartCaptureSessionRequest,
) {
  return request<CaptureSessionResponse>(
    `/api/meetings/${meetingId}/capture-sessions/start`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function registerCaptureChunk(
  meetingId: string,
  payload: RegisterCaptureChunkRequest,
) {
  return request<RegisterCaptureChunkResponse>(
    `/api/meetings/${meetingId}/capture-sessions/chunk`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function completeCaptureChunkUpload(
  meetingId: string,
  payload: CompleteCaptureChunkUploadRequest,
) {
  return request<CompleteCaptureChunkUploadResponse>(
    `/api/meetings/${meetingId}/capture-sessions/chunk/upload-complete`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function runCaptureChunkReasoning(meetingId: string, clientChunkId: string) {
  return request<CompleteCaptureChunkUploadResponse>(
    `/api/meetings/${meetingId}/capture-sessions/chunks/${clientChunkId}/reasoning/run`,
    {
      method: "POST",
    },
  );
}

export function completeCaptureSession(meetingId: string) {
  return request<CaptureSessionResponse>(
    `/api/meetings/${meetingId}/capture-sessions/complete`,
    {
      method: "POST",
    },
  );
}

export function generateActionRecommendations(meetingId: string) {
  return request<ActionRecommendationsResponse>(
    `/api/meetings/${meetingId}/actions/recommendations`,
    {
      method: "POST",
    },
  );
}

export function getActionRecommendations(meetingId: string) {
  return request<ActionRecommendationsResponse>(
    `/api/meetings/${meetingId}/actions/recommendations`,
  );
}

export function searchKnowledge(params: {
  q?: string;
  recordType?: string | null;
  limit?: number;
}) {
  const search = new URLSearchParams();
  if (params.q) search.set("q", params.q);
  if (params.recordType) search.set("recordType", params.recordType);
  if (params.limit) search.set("limit", String(params.limit));
  const qs = search.toString();
  return request<OutcomeSearchResponse>(`/api/knowledge/search${qs ? `?${qs}` : ""}`);
}

export function approveActionRecommendation(
  meetingId: string,
  recommendationId: string,
  payload: ActionApprovalRequest,
) {
  return request<ActionRecommendationResponse>(
    `/api/meetings/${meetingId}/actions/recommendations/${recommendationId}/approve`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function rejectActionRecommendation(
  meetingId: string,
  recommendationId: string,
  payload: ActionApprovalRequest,
) {
  return request<ActionRecommendationResponse>(
    `/api/meetings/${meetingId}/actions/recommendations/${recommendationId}/reject`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function executeActionRecommendation(meetingId: string, recommendationId: string) {
  return request<ActionExecutionResult>(
    `/api/meetings/${meetingId}/actions/recommendations/${recommendationId}/execute`,
    {
      method: "POST",
    },
  );
}

export type { MeetingStreamEvent };
