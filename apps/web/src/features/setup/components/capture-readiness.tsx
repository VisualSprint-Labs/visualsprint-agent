"use client";

import { Mic, Monitor, Video, Volume2, CheckCircle2, AlertCircle } from "lucide-react";

import { Card } from "../../../components/ui/card";
import { useMeetingSession } from "../../meeting-session/context/meeting-session-provider";

const checks = [
  { key: "mediaDevices" as const, label: "Microphone API", icon: Mic },
  { key: "displayCapture" as const, label: "Screen share", icon: Monitor },
  { key: "mediaRecorder" as const, label: "Recording", icon: Video },
  { key: "systemAudio" as const, label: "System audio", icon: Volume2, deriveFrom: "displayCapture" as const },
];

export function CaptureReadiness() {
  const { captureSupport } = useMeetingSession();

  const allOk = checks.every((check) => {
    const ok = check.deriveFrom
      ? captureSupport?.[check.deriveFrom] ?? false
      : captureSupport?.[check.key] ?? false;
    return ok;
  });

  return (
    <Card title="Browser capture readiness" eyebrow="Pre-flight">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {checks.map((check) => {
          const ok = check.deriveFrom
            ? captureSupport?.[check.deriveFrom] ?? false
            : captureSupport?.[check.key] ?? false;
          return (
            <div
              key={check.key}
              className={`group relative flex flex-col items-center gap-2 rounded-xl border p-4 text-center transition-all duration-200 ${
                ok
                  ? "border-[var(--status-live)]/20 bg-[var(--status-live)]/5 hover:border-[var(--status-live)]/40"
                  : "border-border bg-surface-muted hover:border-[var(--status-error)]/30"
              }`}
            >
              <div
                className={`inline-flex h-10 w-10 items-center justify-center rounded-xl transition-all ${
                  ok
                    ? "bg-[var(--status-live)]/10 text-[var(--status-live)]"
                    : "bg-surface-2 text-foreground-subtle"
                }`}
              >
                {ok ? <CheckCircle2 size={18} strokeWidth={2} /> : <AlertCircle size={18} strokeWidth={2} />}
              </div>
              <div>
                <p className="text-xs font-semibold text-foreground">{check.label}</p>
                <p className={`mt-0.5 text-[10px] font-bold uppercase tracking-[0.15em] ${ok ? "text-[var(--status-live)]" : "text-[var(--status-error)]"}`}>
                  {ok ? "Available" : "Unavailable"}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      <div
        className={`mt-5 flex items-start gap-3 rounded-2xl border p-4 text-sm leading-6 transition-all ${
          allOk
            ? "border-[var(--status-live)]/15 bg-[var(--status-live)]/5"
            : "border-border bg-surface-muted"
        }`}
      >
        <div
          className={`mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${
            allOk ? "bg-[var(--status-live)]/10 text-[var(--status-live)]" : "bg-[var(--status-draft)]/10 text-[var(--status-draft)]"
          }`}
        >
          {allOk ? <CheckCircle2 size={14} strokeWidth={2} /> : <AlertCircle size={14} strokeWidth={2} />}
        </div>
        <div>
          <p className="font-semibold text-foreground">
            {allOk ? "Your browser is ready" : "Some features are unavailable"}
          </p>
          <p className="mt-1 text-foreground-muted">
            For browser-based Meet or Zoom, share the meeting tab directly. For desktop Zoom, share
            the Zoom window. Full-screen capture works as a fallback when window capture is not
            available.
          </p>
        </div>
      </div>
    </Card>
  );
}
