"use client";

import { Radio } from "lucide-react";

import { CaptureChunkCard, CaptureSessionSummary } from "../../../components/domain/capture-cards";
import { Card } from "../../../components/ui/card";
import { EmptyState } from "../../../components/ui/empty-state";
import { CaptureStatusPill } from "../../../components/ui/status-pill";
import type { CapturePhase } from "../../meeting-session/types";
import { useMeetingSession } from "../../meeting-session/context/meeting-session-provider";

function captureStatusMessage(phase: CapturePhase) {
  switch (phase) {
    case "requesting":
      return "Requesting screen and microphone access.";
    case "recording":
      return "Capture is recording.";
    case "stopping":
      return "Stopping capture and uploading the final segment.";
    default:
      return "Capture is idle.";
  }
}

export function CapturePanel() {
  const { meeting, capturePhase } = useMeetingSession();

  if (!meeting) {
    return (
      <Card title="Live capture" eyebrow="Browser session">
        <EmptyState title="No meeting selected" body="Choose a meeting to start capture." />
      </Card>
    );
  }

  const activeCaptureSession = meeting.activeCaptureSession;
  const recentChunks = meeting.recentCaptureChunks;
  const isRecording = capturePhase === "recording";

  return (
    <Card title="Live capture" eyebrow="Browser session">
      <div className="space-y-6">
        <p className="sr-only" role="status" aria-live="polite">
          {captureStatusMessage(capturePhase)}
        </p>

        <div
          className={`relative overflow-hidden rounded-2xl border p-5 transition-all duration-300 ${
            isRecording
              ? "border-[var(--status-live)]/30 bg-[var(--status-live)]/5 shadow-glow"
              : "border-border bg-surface-muted"
          }`}
        >
          {isRecording ? (
            <div className="absolute right-4 top-4">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-[var(--status-live)]/15 px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-[var(--status-live)]">
                <Radio size={10} strokeWidth={2.5} className="live-pulse" />
                Recording
              </span>
            </div>
          ) : null}

          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-foreground">
                {isRecording
                  ? "Capturing your screen & audio"
                  : activeCaptureSession
                    ? "Capture session ready"
                    : "Capture not started"}
              </p>
              <div className="mt-2">
                <CaptureSessionSummary
                  hasSession={Boolean(activeCaptureSession)}
                  recorderMimeType={activeCaptureSession?.recorderMimeType}
                  session={activeCaptureSession}
                  status={activeCaptureSession?.status}
                />
              </div>
            </div>
            <CaptureStatusPill
              phase={capturePhase}
              status={activeCaptureSession?.status ?? "idle"}
            />
          </div>
        </div>

        <div className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-foreground-subtle">
            Captured segments
          </p>
          {recentChunks.length === 0 ? (
            <EmptyState
              title="No segments yet"
              body="Each few-second window of screen and audio appears here once capture starts."
            />
          ) : (
            recentChunks.map((chunk) => <CaptureChunkCard key={chunk.id} chunk={chunk} />)
          )}
        </div>
      </div>
    </Card>
  );
}
