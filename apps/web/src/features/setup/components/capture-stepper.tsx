"use client";

import { captureStages } from "@visualsprint/contracts";
import type { MeetingDetail } from "@visualsprint/contracts";
import { CheckCircle2, Loader2 } from "lucide-react";

function stageState(
  stageId: string,
  meeting: MeetingDetail | null,
  capturePhase: string,
) {
  if (!meeting) {
    return stageId === "meeting" ? "current" : "upcoming";
  }

  if (stageId === "meeting") {
    return meeting.status !== "draft" ? "complete" : "current";
  }

  if (stageId === "capture") {
    if (meeting.status === "draft") {
      return "upcoming";
    }
    if (capturePhase === "recording" || meeting.activeCaptureSession) {
      return "complete";
    }
    return meeting.status === "live" ? "current" : "upcoming";
  }

  if (stageId === "chunking") {
    if (meeting.metrics.captureChunksCount > 0) {
      return "complete";
    }
    return capturePhase === "recording" ? "current" : "upcoming";
  }

  if (stageId === "processing") {
    if (meeting.metrics.decisionsCount > 0 || meeting.metrics.transcriptSegmentsCount > 0) {
      return "complete";
    }
    return meeting.metrics.captureChunksCount > 0 ? "current" : "upcoming";
  }

  return "upcoming";
}

export function CaptureStepper({
  meeting,
  capturePhase,
}: {
  meeting: MeetingDetail | null;
  capturePhase: string;
}) {
  return (
    <div className="relative">
      {/* connector line */}
      <div className="absolute left-6 top-8 hidden h-0.5 w-[calc(100%-3rem)] bg-border md:block" />

      <ol className="grid gap-4 md:grid-cols-4">
        {captureStages.map((stage, i) => {
          const state = stageState(stage.id, meeting, capturePhase);
          const isComplete = state === "complete";
          const isCurrent = state === "current";

          return (
            <li
              key={stage.id}
              className={`relative rounded-2xl border p-5 transition-all duration-300 ${
                isComplete
                  ? "border-[var(--status-live)]/20 bg-[var(--status-live)]/5"
                  : isCurrent
                    ? "border-brand/30 bg-brand/5 shadow-sm ring-1 ring-brand/10"
                    : "border-border bg-surface-muted/50"
              }`}
            >
              <div className="flex items-center gap-3 mb-3">
                <div
                  className={`relative z-10 inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border-2 text-sm font-bold transition-all duration-300 ${
                    isComplete
                      ? "border-[var(--status-live)] bg-[var(--status-live)]/10 text-[var(--status-live)]"
                      : isCurrent
                        ? "border-brand bg-brand/10 text-brand"
                        : "border-border bg-surface text-foreground-subtle"
                  }`}
                >
                  {isComplete ? (
                    <CheckCircle2 size={18} strokeWidth={2.5} />
                  ) : isCurrent ? (
                    <Loader2 size={16} strokeWidth={2.5} className="animate-spin" />
                  ) : (
                    <span className="text-xs">{i + 1}</span>
                  )}
                </div>
                <div className="min-w-0">
                  <p
                    className={`text-[10px] font-bold uppercase tracking-[0.18em] ${
                      isComplete
                        ? "text-[var(--status-live)]"
                        : isCurrent
                          ? "text-brand"
                          : "text-foreground-subtle"
                    }`}
                  >
                    {isComplete ? "Complete" : isCurrent ? "In progress" : "Upcoming"}
                  </p>
                  <p className="text-sm font-semibold text-foreground truncate">{stage.label}</p>
                </div>
              </div>
              <p className="text-xs leading-5 text-foreground-muted line-clamp-2">{stage.description}</p>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
