"use client";

import type {
  ActionRecommendation,
  AgentSmokeResponse,
  AgentInvocationAuditResponse,
  ChunkInsight,
  CreateMeetingRequest,
  FinalReport,
  IndexedOutcomeDocument,
  MeetingDetail,
  MeetingSummary,
  MeetingSummaryPacket,
  PlatformMetaResponse,
} from "@visualsprint/contracts";
import { useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  startTransition,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  approveActionRecommendation,
  createMeeting,
  endMeeting,
  executeActionRecommendation,
  finalizeReport,
  generateActionRecommendations,
  getActionRecommendations,
  getAgentInvocationAudit,
  getChunkInsight,
  getFinalReport,
  getIndexedOutcomeDocuments,
  getMeeting,
  getPlatformMeta,
  getSummaryPacket,
  listMeetings,
  rejectActionRecommendation,
  runAgentSmoke,
  startMeeting,
} from "../../../lib/api";
import { useToast } from "../../../components/providers/toast-provider";
import { useCaptureSupport } from "../../../hooks/use-capture-support";
import { useMeetingStream } from "../../../hooks/use-meeting-stream";
import { getErrorMessage } from "../../../lib/format";
import { queryKeys } from "../../../lib/query-keys";
import { toMeetingSummary, upsertMeetingSummary } from "../../../lib/meeting";
import { useBrowserCapture } from "../hooks/use-browser-capture";

const initialDraft: CreateMeetingRequest = {
  title: "Team planning sync",
  participantCount: 4,
  sourceConnector: "browser_live_capture",
  notes: "Focus on decisions, owners, blockers, and next steps.",
};

type MeetingSessionContextValue = {
  meetingId: string | undefined;
  meeting: MeetingDetail | null;
  meetings: MeetingSummary[];
  draft: CreateMeetingRequest;
  setDraft: React.Dispatch<React.SetStateAction<CreateMeetingRequest>>;
  isBusy: boolean;
  error: string | null;
  clearError: () => void;
  streamStatus: ReturnType<typeof useMeetingStream>;
  capturePhase: ReturnType<typeof useBrowserCapture>["capturePhase"];
  canStartCapture: boolean;
  finalReport: FinalReport | null;
  chunkInsight: ChunkInsight | null;
  summaryPacket: MeetingSummaryPacket | null;
  indexedOutcomes: IndexedOutcomeDocument[];
  platformMeta: PlatformMetaResponse | null;
  agentInvocationAudit: AgentInvocationAuditResponse | null;
  agentSmokeResult: AgentSmokeResponse | null;
  actionRecommendations: ActionRecommendation[];
  captureSupport: ReturnType<typeof useCaptureSupport>;
  refreshMeetings: () => Promise<MeetingSummary[]>;
  selectMeeting: (id: string) => Promise<void>;
  createMeetingFromDraft: (event?: React.FormEvent) => Promise<MeetingDetail | null>;
  startMeetingSession: (targetId?: string) => Promise<boolean>;
  endMeetingSession: () => Promise<boolean>;
  beginBrowserCapture: () => Promise<void>;
  stopBrowserCapture: () => Promise<void>;
  runAgentSmokeCheck: () => Promise<void>;
  generateRecommendations: () => Promise<void>;
  approveRecommendation: (id: string) => Promise<void>;
  rejectRecommendation: (id: string) => Promise<void>;
  executeRecommendation: (id: string) => Promise<void>;
  refreshFinalReport: () => Promise<boolean>;
};

const MeetingSessionContext = createContext<MeetingSessionContextValue | null>(null);

export function MeetingSessionProvider({
  meetingId,
  loadDevMeta = false,
  children,
}: {
  meetingId?: string;
  loadDevMeta?: boolean;
  children: ReactNode;
}) {
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const captureSupport = useCaptureSupport();

  const fail = useCallback(
    (message: string) => {
      setError(message);
      pushToast(message, "error");
    },
    [pushToast],
  );

  const succeed = useCallback(
    (message: string) => {
      pushToast(message, "success");
    },
    [pushToast],
  );

  const [draft, setDraft] = useState<CreateMeetingRequest>(initialDraft);
  const [meetings, setMeetings] = useState<MeetingSummary[]>([]);
  const [meeting, setMeeting] = useState<MeetingDetail | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [finalReport, setFinalReport] = useState<FinalReport | null>(null);
  const [chunkInsight, setChunkInsight] = useState<ChunkInsight | null>(null);
  const [summaryPacket, setSummaryPacket] = useState<MeetingSummaryPacket | null>(null);
  const [indexedOutcomes, setIndexedOutcomes] = useState<IndexedOutcomeDocument[]>([]);
  const [platformMeta, setPlatformMeta] = useState<PlatformMetaResponse | null>(null);
  const [agentInvocationAudit, setAgentInvocationAudit] =
    useState<AgentInvocationAuditResponse | null>(null);
  const [agentSmokeResult, setAgentSmokeResult] = useState<AgentSmokeResponse | null>(null);
  const [actionRecommendations, setActionRecommendations] = useState<ActionRecommendation[]>([]);

  const applyMeeting = useCallback(
    (nextMeeting: MeetingDetail) => {
      startTransition(() => {
        setMeeting(nextMeeting);
        setMeetings((current) => upsertMeetingSummary(current, toMeetingSummary(nextMeeting)));
      });
      queryClient.setQueryData(queryKeys.meeting(nextMeeting.id), { meeting: nextMeeting });
    },
    [queryClient],
  );

  const streamStatus = useMeetingStream(meeting?.id, applyMeeting);

  const onError = useCallback(
    (message: string) => {
      fail(message);
    },
    [fail],
  );

  const { capturePhase, canStartCapture, beginBrowserCapture, stopBrowserCapture } =
    useBrowserCapture({
      meeting,
      captureSupport,
      onMeetingUpdated: applyMeeting,
      onError,
    });

  const refreshMeetings = useCallback(async () => {
    const response = await listMeetings();
    startTransition(() => {
      setMeetings(response.meetings);
    });
    queryClient.setQueryData(queryKeys.meetings, response);
    return response.meetings;
  }, [queryClient]);

  const selectMeeting = useCallback(
    async (id: string) => {
      setError(null);
      const response = await getMeeting(id);
      applyMeeting(response.meeting);
    },
    [applyMeeting],
  );

  useEffect(() => {
    void (async () => {
      setError(null);
      try {
        if (loadDevMeta) {
          const [metaResponse, auditResponse] = await Promise.all([
            getPlatformMeta(),
            getAgentInvocationAudit(),
          ]);
          setPlatformMeta(metaResponse);
          setAgentInvocationAudit(auditResponse);
        }
        const meetingList = await refreshMeetings();
        if (meetingId) {
          await selectMeeting(meetingId);
        } else if (loadDevMeta && meetingList[0]?.id) {
          await selectMeeting(meetingList[0].id);
        } else {
          startTransition(() => {
            setMeeting(null);
            setFinalReport(null);
            setActionRecommendations([]);
          });
        }
      } catch (loadError) {
        fail(getErrorMessage(loadError));
      }
    })();
  }, [fail, loadDevMeta, meetingId, refreshMeetings, selectMeeting]);

  useEffect(() => {
    if (!meetingId || !meeting || meeting.id !== meetingId || meeting.status !== "draft") {
      return;
    }
    setDraft({
      title: meeting.title,
      participantCount: meeting.participantCount,
      sourceConnector: meeting.sourceConnector,
      notes: meeting.notes,
    });
  }, [meeting, meetingId]);

  useEffect(() => {
    if (!loadDevMeta || !meeting?.id) {
      return;
    }
    void (async () => {
      try {
        const auditResponse = await getAgentInvocationAudit();
        setAgentInvocationAudit(auditResponse);
      } catch {
        setAgentInvocationAudit(null);
      }
    })();
  }, [
    loadDevMeta,
    meeting?.id,
    meeting?.latestEvents,
    meeting?.metrics.captureChunksCount,
    meeting?.metrics.decisionsCount,
    meeting?.metrics.commitmentsCount,
    meeting?.metrics.blockersCount,
    meeting?.metrics.openQuestionsCount,
  ]);

  useEffect(() => {
    if (!meeting?.id || meeting.status !== "ended") {
      return;
    }
    void (async () => {
      try {
        const reportResponse = await getFinalReport(meeting.id);
        setFinalReport(reportResponse.report);
      } catch {
        try {
          const reportResponse = await finalizeReport(meeting.id);
          setFinalReport(reportResponse.report);
        } catch (reportError) {
          fail(getErrorMessage(reportError));
        }
      }
    })();
  }, [fail, meeting?.id, meeting?.status]);

  useEffect(() => {
    const latestChunk = meeting?.recentCaptureChunks[0];
    if (!meeting?.id || !latestChunk || latestChunk.processingStatus !== "processed") {
      setChunkInsight(null);
      return;
    }
    void (async () => {
      try {
        const insightResponse = await getChunkInsight(meeting.id, latestChunk.clientChunkId);
        setChunkInsight(insightResponse.insight);
      } catch {
        setChunkInsight(null);
      }
    })();
  }, [meeting?.id, meeting?.recentCaptureChunks]);

  useEffect(() => {
    if (!meeting?.id) {
      setSummaryPacket(null);
      return;
    }
    void (async () => {
      try {
        const summaryResponse = await getSummaryPacket(meeting.id);
        setSummaryPacket(summaryResponse.summaryPacket);
      } catch {
        setSummaryPacket(null);
      }
    })();
  }, [
    meeting?.id,
    meeting?.latestEvents,
    meeting?.metrics.decisionsCount,
    meeting?.metrics.commitmentsCount,
    meeting?.metrics.blockersCount,
    meeting?.metrics.openQuestionsCount,
    meeting?.metrics.memoryMatchesCount,
  ]);

  useEffect(() => {
    if (!meeting?.id) {
      setIndexedOutcomes([]);
      return;
    }
    void (async () => {
      try {
        const response = await getIndexedOutcomeDocuments(meeting.id);
        setIndexedOutcomes(response.documents);
      } catch {
        setIndexedOutcomes([]);
      }
    })();
  }, [
    meeting?.id,
    meeting?.metrics.decisionsCount,
    meeting?.metrics.commitmentsCount,
    meeting?.metrics.blockersCount,
    meeting?.metrics.openQuestionsCount,
  ]);

  useEffect(() => {
    if (!meeting?.id) {
      setActionRecommendations([]);
      return;
    }
    void (async () => {
      try {
        const response = await getActionRecommendations(meeting.id);
        setActionRecommendations(response.recommendations);
      } catch {
        setActionRecommendations([]);
      }
    })();
  }, [meeting?.id, meeting?.metrics.actionRecommendationsCount]);

  const createMeetingFromDraft = useCallback(
    async (event?: React.FormEvent) => {
      event?.preventDefault();
      setIsBusy(true);
      setError(null);
      try {
        const response = await createMeeting(draft);
        applyMeeting(response.meeting);
        await refreshMeetings();
        succeed("Meeting created.");
        return response.meeting;
      } catch (submitError) {
        fail(getErrorMessage(submitError));
        return null;
      } finally {
        setIsBusy(false);
      }
    },
    [applyMeeting, draft, fail, refreshMeetings, succeed],
  );

  const startMeetingSession = useCallback(async (targetId?: string) => {
    const id = targetId ?? meeting?.id;
    if (!id) {
      return false;
    }
    setIsBusy(true);
    setError(null);
    try {
      const response = await startMeeting(id);
      applyMeeting(response.meeting);
      await refreshMeetings();
      succeed("Meeting started.");
      return true;
    } catch (actionError) {
      fail(getErrorMessage(actionError));
      return false;
    } finally {
      setIsBusy(false);
    }
  }, [applyMeeting, fail, meeting, refreshMeetings, succeed]);

  const endMeetingSession = useCallback(async () => {
    if (!meeting) {
      return false;
    }
    setIsBusy(true);
    setError(null);
    try {
      if (capturePhase === "recording") {
        await stopBrowserCapture();
      }
      const response = await endMeeting(meeting.id);
      applyMeeting(response.meeting);
      const reportResponse = await finalizeReport(meeting.id);
      setFinalReport(reportResponse.report);
      await refreshMeetings();
      succeed("Meeting ended. Report is ready.");
      return true;
    } catch (actionError) {
      fail(getErrorMessage(actionError));
      return false;
    } finally {
      setIsBusy(false);
    }
  }, [applyMeeting, capturePhase, fail, meeting, refreshMeetings, stopBrowserCapture, succeed]);

  const runAgentSmokeCheck = useCallback(async () => {
    if (!meeting) {
      return;
    }
    setIsBusy(true);
    setError(null);
    try {
      const latestProcessedChunk = meeting.recentCaptureChunks.find(
        (chunk) => chunk.processingStatus === "processed",
      );
      const response = await runAgentSmoke(meeting.id, latestProcessedChunk?.clientChunkId);
      setAgentSmokeResult(response);
      const auditResponse = await getAgentInvocationAudit();
      setAgentInvocationAudit(auditResponse);
    } catch (smokeError) {
      fail(getErrorMessage(smokeError));
    } finally {
      setIsBusy(false);
    }
  }, [fail, meeting]);

  const generateRecommendations = useCallback(async () => {
    if (!meeting) {
      return;
    }
    setIsBusy(true);
    setError(null);
    try {
      const response = await generateActionRecommendations(meeting.id);
      setActionRecommendations(response.recommendations);
      await selectMeeting(meeting.id);
      succeed("Action recommendations generated.");
    } catch (genError) {
      fail(getErrorMessage(genError));
    } finally {
      setIsBusy(false);
    }
  }, [fail, meeting, selectMeeting, succeed]);

  const approveRecommendation = useCallback(
    async (recommendationId: string) => {
      if (!meeting) {
        return;
      }
      setIsBusy(true);
      setError(null);
      try {
        await approveActionRecommendation(meeting.id, recommendationId, {
          approved: true,
          note: "Approved in portal",
        });
        await selectMeeting(meeting.id);
        const response = await getActionRecommendations(meeting.id);
        setActionRecommendations(response.recommendations);
        succeed("Recommendation approved.");
      } catch (err) {
        fail(getErrorMessage(err));
      } finally {
        setIsBusy(false);
      }
    },
    [fail, meeting, selectMeeting, succeed],
  );

  const rejectRecommendation = useCallback(
    async (recommendationId: string) => {
      if (!meeting) {
        return;
      }
      setIsBusy(true);
      setError(null);
      try {
        await rejectActionRecommendation(meeting.id, recommendationId, {
          approved: false,
          note: "Rejected in portal",
        });
        await selectMeeting(meeting.id);
        const response = await getActionRecommendations(meeting.id);
        setActionRecommendations(response.recommendations);
        succeed("Recommendation rejected.");
      } catch (err) {
        fail(getErrorMessage(err));
      } finally {
        setIsBusy(false);
      }
    },
    [fail, meeting, selectMeeting, succeed],
  );

  const refreshFinalReport = useCallback(async () => {
    if (!meeting?.id || meeting.status !== "ended") {
      return false;
    }
    setIsBusy(true);
    setError(null);
    try {
      try {
        const reportResponse = await getFinalReport(meeting.id);
        setFinalReport(reportResponse.report);
      } catch {
        const reportResponse = await finalizeReport(meeting.id);
        setFinalReport(reportResponse.report);
      }
      return true;
    } catch (reportError) {
      fail(getErrorMessage(reportError));
      return false;
    } finally {
      setIsBusy(false);
    }
  }, [fail, meeting?.id, meeting?.status]);

  const executeRecommendation = useCallback(
    async (recommendationId: string) => {
      if (!meeting) {
        return;
      }
      setIsBusy(true);
      setError(null);
      try {
        await executeActionRecommendation(meeting.id, recommendationId);
        await selectMeeting(meeting.id);
        const response = await getActionRecommendations(meeting.id);
        setActionRecommendations(response.recommendations);
        succeed("Action executed.");
      } catch (err) {
        fail(getErrorMessage(err));
      } finally {
        setIsBusy(false);
      }
    },
    [fail, meeting, selectMeeting, succeed],
  );

  const value = useMemo<MeetingSessionContextValue>(
    () => ({
      meetingId,
      meeting,
      meetings,
      draft,
      setDraft,
      isBusy,
      error,
      clearError: () => setError(null),
      streamStatus,
      capturePhase,
      canStartCapture,
      finalReport,
      chunkInsight,
      summaryPacket,
      indexedOutcomes,
      platformMeta,
      agentInvocationAudit,
      agentSmokeResult,
      actionRecommendations,
      captureSupport,
      refreshMeetings,
      selectMeeting,
      createMeetingFromDraft,
      startMeetingSession,
      endMeetingSession,
      beginBrowserCapture,
      stopBrowserCapture,
      runAgentSmokeCheck,
      generateRecommendations,
      approveRecommendation,
      rejectRecommendation,
      executeRecommendation,
      refreshFinalReport,
    }),
    [
      meetingId,
      meeting,
      meetings,
      draft,
      isBusy,
      error,
      streamStatus,
      capturePhase,
      canStartCapture,
      finalReport,
      chunkInsight,
      summaryPacket,
      indexedOutcomes,
      platformMeta,
      agentInvocationAudit,
      agentSmokeResult,
      actionRecommendations,
      captureSupport,
      refreshMeetings,
      selectMeeting,
      createMeetingFromDraft,
      startMeetingSession,
      endMeetingSession,
      beginBrowserCapture,
      stopBrowserCapture,
      runAgentSmokeCheck,
      generateRecommendations,
      approveRecommendation,
      rejectRecommendation,
      executeRecommendation,
      refreshFinalReport,
    ],
  );

  return (
    <MeetingSessionContext.Provider value={value}>{children}</MeetingSessionContext.Provider>
  );
}

export function useMeetingSession() {
  const context = useContext(MeetingSessionContext);
  if (!context) {
    throw new Error("useMeetingSession must be used within MeetingSessionProvider");
  }
  return context;
}
