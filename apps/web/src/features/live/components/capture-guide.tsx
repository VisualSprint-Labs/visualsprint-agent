"use client";

import {
  Play,
  Square,
  MonitorUp,
  Sparkles,
  FileText,
  Loader2,
  CheckCircle2,
  Mic,
  Shield,
} from "lucide-react";

import { Button } from "../../../components/ui/button";
import { useMeetingSession } from "../../meeting-session/context/meeting-session-provider";

/**
 * Phase-aware onboarding guide for the live capture screen.
 *
 * The single most common confusion is "what do I actually do here?". This panel
 * answers that question explicitly for whatever phase the session is in, and
 * surfaces the primary action right next to the explanation.
 */
export function CaptureGuide() {
  const {
    meeting,
    capturePhase,
    canStartCapture,
    beginBrowserCapture,
    stopBrowserCapture,
  } = useMeetingSession();

  if (!meeting) {
    return null;
  }

  const isRecording = capturePhase === "recording";
  const isRequesting = capturePhase === "requesting";
  const isStopping = capturePhase === "stopping";

  // ---- Recording: reassure + tell them how to finish -----------------------
  if (isRecording) {
    return (
      <GuideShell
        tone="live"
        badge="You're live"
        icon={<CheckCircle2 size={18} strokeWidth={2.5} />}
        title="VisualSprint is watching and listening"
        body="Just run your meeting as normal. Every few seconds it reads your screen and the conversation, then surfaces decisions, blockers, and action items in the panels below — no clicking required."
      >
        <div className="flex flex-wrap items-center gap-3">
          <Button
            variant="danger"
            leftIcon={<Square size={16} strokeWidth={2.5} />}
            onClick={() => void stopBrowserCapture()}
          >
            End capture &amp; build report
          </Button>
          <span className="text-xs text-foreground-muted">
            Finish when the meeting ends — you&apos;ll get a summary plus Jira &amp; Slack suggestions.
          </span>
        </div>
      </GuideShell>
    );
  }

  // ---- Requesting: explain the browser share prompt ------------------------
  if (isRequesting) {
    return (
      <GuideShell
        tone="brand"
        badge="Step 1 of 3"
        icon={<MonitorUp size={18} strokeWidth={2.5} />}
        title="Choose what to share"
        body="Your browser is asking which screen, window, or tab to capture. Pick the one your meeting is on (or “Entire Screen”), then click Share. Tick “Also share tab/system audio” so VisualSprint can hear the discussion."
      >
        <span className="inline-flex items-center gap-2 text-xs font-medium text-foreground-muted">
          <Loader2 size={14} strokeWidth={2.5} className="animate-spin" />
          Waiting for you to pick a screen…
        </span>
      </GuideShell>
    );
  }

  // ---- Stopping ------------------------------------------------------------
  if (isStopping) {
    return (
      <GuideShell
        tone="brand"
        badge="Wrapping up"
        icon={<Loader2 size={18} strokeWidth={2.5} className="animate-spin" />}
        title="Processing your final moments"
        body="We're analysing the last segment and assembling your report. This only takes a moment — you'll be taken to the summary automatically."
      />
    );
  }

  // ---- Idle: the first-run "how it works" + primary CTA --------------------
  return (
    <GuideShell
      tone="brand"
      badge="Ready to start"
      icon={<Sparkles size={18} strokeWidth={2.5} />}
      title="Turn this meeting into decisions — here's how"
      body="VisualSprint captures your screen and the conversation, then an AI agent writes up what was decided, what's blocked, and who owns what."
    >
      <ol className="mb-5 grid gap-3 sm:grid-cols-3">
        <GuideStep
          n={1}
          icon={<MonitorUp size={15} strokeWidth={2.5} />}
          title="Begin & share"
          body="Click Begin capture, then choose the screen or tab to share."
        />
        <GuideStep
          n={2}
          icon={<Mic size={15} strokeWidth={2.5} />}
          title="Run your meeting"
          body="Talk normally — insights appear below automatically as you go."
        />
        <GuideStep
          n={3}
          icon={<FileText size={15} strokeWidth={2.5} />}
          title="Get your report"
          body="End the meeting for a summary plus Jira & Slack actions."
        />
      </ol>

      <div className="flex flex-wrap items-center gap-3">
        <Button
          size="lg"
          leftIcon={<Play size={18} strokeWidth={2.5} />}
          disabled={!canStartCapture}
          onClick={() => void beginBrowserCapture()}
        >
          Begin capture
        </Button>
        {!canStartCapture ? (
          <span className="text-xs text-foreground-muted">
            Make sure the meeting is live and your browser supports screen capture.
          </span>
        ) : (
          <span className="text-xs text-foreground-muted">
            You&apos;ll be asked which screen or tab to share next.
          </span>
        )}
      </div>

      <p className="mt-4 flex items-start gap-2 text-xs leading-5 text-foreground-subtle">
        <Shield size={14} strokeWidth={2} className="mt-0.5 shrink-0 text-foreground-muted" />
        <span>
          No silent recording. No hidden sharing. VisualSprint only captures meetings your team
          starts, then uses that context to create your private reports and approved workflow actions.
        </span>
      </p>
    </GuideShell>
  );
}

function GuideShell({
  tone,
  badge,
  icon,
  title,
  body,
  children,
}: {
  tone: "brand" | "live";
  badge: string;
  icon: React.ReactNode;
  title: string;
  body: string;
  children?: React.ReactNode;
}) {
  const accent =
    tone === "live"
      ? "border-[var(--status-live)]/30 bg-[var(--status-live)]/[0.06]"
      : "border-brand/25 bg-brand/[0.05]";
  const chip =
    tone === "live"
      ? "bg-[var(--status-live)]/15 text-[var(--status-live)]"
      : "bg-brand/15 text-brand";
  const iconWrap =
    tone === "live"
      ? "bg-[var(--status-live)]/12 text-[var(--status-live)]"
      : "bg-brand/12 text-brand";

  return (
    <section
      className={`rounded-2xl border p-5 shadow-sm transition-all duration-300 sm:p-6 ${accent}`}
    >
      <div className="flex items-start gap-4">
        <div
          className={`hidden h-11 w-11 shrink-0 items-center justify-center rounded-xl sm:inline-flex ${iconWrap}`}
        >
          {icon}
        </div>
        <div className="min-w-0 flex-1">
          <span
            className={`mb-2 inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-[0.16em] ${chip}`}
          >
            {badge}
          </span>
          <h2 className="text-lg font-bold tracking-tight text-foreground text-balance sm:text-xl">
            {title}
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-foreground-muted">{body}</p>
          {children ? <div className="mt-5">{children}</div> : null}
        </div>
      </div>
    </section>
  );
}

function GuideStep({
  n,
  icon,
  title,
  body,
}: {
  n: number;
  icon: React.ReactNode;
  title: string;
  body: string;
}) {
  return (
    <li className="rounded-xl border border-border bg-surface/70 p-3.5">
      <div className="mb-2 flex items-center gap-2">
        <span className="inline-flex h-6 w-6 items-center justify-center rounded-lg bg-brand/10 text-[11px] font-bold text-brand">
          {n}
        </span>
        <span className="text-brand">{icon}</span>
        <p className="text-sm font-semibold text-foreground">{title}</p>
      </div>
      <p className="text-xs leading-5 text-foreground-muted">{body}</p>
    </li>
  );
}
