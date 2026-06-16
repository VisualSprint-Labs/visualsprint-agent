import type {
  BlockerRecord,
  CaptureChunkSummary,
  CommitmentRecord,
  DecisionRecord,
  EvidenceReference,
  FinalReport,
  MemoryMatch,
  OpenQuestionRecord,
  ScreenEvent,
  TranscriptSegment,
} from "@visualsprint/contracts";
import {
  GitCommitHorizontal,
  CheckCircle2,
  OctagonAlert,
  HelpCircle,
  BrainCircuit,
} from "lucide-react";

import {
  formatFrameTimestamp,
  formatProcessingSourceMode,
  formatScreenEventKind,
  formatTimestamp,
} from "../../lib/format";
import { RecordStatusBadge } from "../ui/status-pill";
import { EvidenceList } from "./evidence-list";

export function SourceModeBadge({
  label,
  mode,
}: {
  label: string;
  mode: CaptureChunkSummary["transcriptSource"] | FinalReport["summarySource"];
}) {
  const className =
    mode === "downstream_service"
      ? "bg-[var(--status-processing)]/15 text-[var(--status-processing)]"
      : "bg-surface-muted text-foreground-muted";

  return (
    <span className={`rounded-lg px-2.5 py-1 text-xs font-medium uppercase tracking-[0.12em] ${className}`}>
      {label} {formatProcessingSourceMode(mode)}
    </span>
  );
}

export function DecisionCard({
  decision,
  onEvidenceSelect,
}: {
  decision: DecisionRecord;
  onEvidenceSelect?: (reference: EvidenceReference) => void;
}) {
  return (
    <article className="group relative overflow-hidden rounded-xl border border-border bg-surface-muted p-4 transition-all duration-200 hover:border-brand/30 hover:shadow-md hover:-translate-y-0.5">
      <div className="absolute left-0 top-0 h-full w-1 bg-brand/60 opacity-0 transition-opacity group-hover:opacity-100" />
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <div className="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-brand/10">
            <GitCommitHorizontal size={14} strokeWidth={2} className="text-brand" />
          </div>
          <p className="text-sm font-semibold text-foreground">{decision.title}</p>
        </div>
        <RecordStatusBadge status={decision.status} />
      </div>
      <p className="mt-2 pl-9 text-sm leading-6 text-foreground-muted">{decision.rationale}</p>
      <div className="pl-9">
        <EvidenceList evidence={decision.evidence} onSelect={onEvidenceSelect} />
      </div>
      <p className="mt-3 pl-9 text-xs uppercase tracking-[0.16em] text-foreground-subtle">
        {decision.speakerLabel} · {decision.firstSeenChunkId} → {decision.lastUpdatedChunkId}
      </p>
      <p className="mt-1.5 pl-9 text-xs text-foreground-subtle">{formatTimestamp(decision.recordedAt)}</p>
    </article>
  );
}

export function CommitmentCard({
  commitment,
  onEvidenceSelect,
}: {
  commitment: CommitmentRecord;
  onEvidenceSelect?: (reference: EvidenceReference) => void;
}) {
  return (
    <article className="group relative overflow-hidden rounded-xl border border-border bg-surface-muted p-4 transition-all duration-200 hover:border-[var(--accent)]/30 hover:shadow-md hover:-translate-y-0.5">
      <div className="absolute left-0 top-0 h-full w-1 bg-[var(--accent)]/60 opacity-0 transition-opacity group-hover:opacity-100" />
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <div className="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[var(--accent)]/10">
            <CheckCircle2 size={14} strokeWidth={2} className="text-[var(--accent)]" />
          </div>
          <p className="text-sm font-semibold text-foreground">{commitment.ownerLabel}</p>
        </div>
        <RecordStatusBadge status={commitment.status} />
      </div>
      <p className="mt-2 pl-9 text-sm leading-6 text-foreground-muted">{commitment.action}</p>
      <div className="pl-9">
        <EvidenceList evidence={commitment.evidence} onSelect={onEvidenceSelect} />
      </div>
      <p className="mt-3 pl-9 text-xs uppercase tracking-[0.16em] text-foreground-subtle">
        Due {commitment.dueHint} · {commitment.firstSeenChunkId} → {commitment.lastUpdatedChunkId}
      </p>
      <p className="mt-1.5 pl-9 text-xs text-foreground-subtle">{formatTimestamp(commitment.recordedAt)}</p>
    </article>
  );
}

export function BlockerCard({
  blocker,
  onEvidenceSelect,
}: {
  blocker: BlockerRecord;
  onEvidenceSelect?: (reference: EvidenceReference) => void;
}) {
  return (
    <article className="group relative overflow-hidden rounded-xl border border-border bg-surface-muted p-4 transition-all duration-200 hover:border-[var(--status-error)]/30 hover:shadow-md hover:-translate-y-0.5">
      <div className="absolute left-0 top-0 h-full w-1 bg-[var(--status-error)]/60 opacity-0 transition-opacity group-hover:opacity-100" />
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <div className="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[var(--status-error)]/10">
            <OctagonAlert size={14} strokeWidth={2} className="text-[var(--status-error)]" />
          </div>
          <p className="text-sm font-semibold text-foreground">{blocker.summary}</p>
        </div>
        <div className="flex gap-2">
          <span className="rounded-lg bg-[var(--status-draft)]/15 px-2.5 py-1 text-xs font-medium uppercase tracking-[0.12em] text-[var(--status-draft)]">
            {blocker.severity}
          </span>
          <RecordStatusBadge status={blocker.status} />
        </div>
      </div>
      <div className="pl-9">
        <EvidenceList evidence={blocker.evidence} onSelect={onEvidenceSelect} />
      </div>
      <p className="mt-3 pl-9 text-xs uppercase tracking-[0.16em] text-foreground-subtle">
        Owner {blocker.ownerLabel} · {blocker.firstSeenChunkId} → {blocker.lastUpdatedChunkId}
      </p>
      <p className="mt-1.5 pl-9 text-xs text-foreground-subtle">{formatTimestamp(blocker.recordedAt)}</p>
    </article>
  );
}

export function MemoryMatchCard({ memoryMatch }: { memoryMatch: MemoryMatch }) {
  const isRecurring =
    memoryMatch.relation === "recurring" || memoryMatch.relation === "reopened";

  return (
    <article
      className={`group relative overflow-hidden rounded-xl border p-4 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md ${
        isRecurring
          ? "border-[var(--accent-memory)]/30 bg-[var(--accent-memory)]/10 hover:border-[var(--accent-memory)]/50"
          : "border-border bg-surface-muted hover:border-[var(--accent-memory)]/30"
      }`}
    >
      <div className="absolute left-0 top-0 h-full w-1 bg-[var(--accent-memory)]/60 opacity-0 transition-opacity group-hover:opacity-100" />
      <div className="flex items-start gap-2.5">
        <div className="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[var(--accent-memory)]/10">
          <BrainCircuit size={14} strokeWidth={2} className="text-[var(--accent-memory)]" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-foreground">{memoryMatch.summary}</p>
          <p className="mt-2 text-sm leading-6 text-foreground-muted">
            Source meeting: {memoryMatch.sourceMeetingTitle}
          </p>
          <p className="mt-2 text-sm leading-6 text-foreground-muted">{memoryMatch.snippet}</p>
          <p className="mt-3 text-xs uppercase tracking-[0.16em] text-foreground-subtle">
            {memoryMatch.relation} · {memoryMatch.strength} · score {memoryMatch.score.toFixed(2)}
          </p>
          <p className="mt-1.5 text-xs text-foreground-subtle">
            {memoryMatch.sourceMeetingId} · {formatTimestamp(memoryMatch.recordedAt)}
          </p>
        </div>
      </div>
    </article>
  );
}

export function OpenQuestionCard({
  openQuestion,
  onEvidenceSelect,
}: {
  openQuestion: OpenQuestionRecord;
  onEvidenceSelect?: (reference: EvidenceReference) => void;
}) {
  return (
    <article className="group relative overflow-hidden rounded-xl border border-border bg-surface-muted p-4 transition-all duration-200 hover:border-[var(--status-processing)]/30 hover:shadow-md hover:-translate-y-0.5">
      <div className="absolute left-0 top-0 h-full w-1 bg-[var(--status-processing)]/60 opacity-0 transition-opacity group-hover:opacity-100" />
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <div className="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[var(--status-processing)]/10">
            <HelpCircle size={14} strokeWidth={2} className="text-[var(--status-processing)]" />
          </div>
          <p className="text-sm font-semibold text-foreground">{openQuestion.question}</p>
        </div>
        <RecordStatusBadge status={openQuestion.status} />
      </div>
      <div className="pl-9">
        <EvidenceList evidence={openQuestion.evidence} onSelect={onEvidenceSelect} />
      </div>
      <p className="mt-3 pl-9 text-xs uppercase tracking-[0.16em] text-foreground-subtle">
        {openQuestion.speakerLabel} · {openQuestion.firstSeenChunkId} → {openQuestion.lastUpdatedChunkId}
      </p>
      <p className="mt-1.5 pl-9 text-xs text-foreground-subtle">{formatTimestamp(openQuestion.recordedAt)}</p>
    </article>
  );
}

export function TranscriptCard({ segment }: { segment: TranscriptSegment }) {
  return (
    <article className="rounded-xl border border-border bg-surface p-4 transition hover:border-brand/20">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-foreground">{segment.speakerLabel}</p>
          <p className="mt-2 text-sm leading-6 text-foreground-muted">{segment.text}</p>
        </div>
        <span className="whitespace-nowrap text-xs text-foreground-subtle">
          {formatTimestamp(segment.startedAt)}
        </span>
      </div>
    </article>
  );
}

export function ScreenEventCard({ screenEvent }: { screenEvent: ScreenEvent }) {
  return (
    <article className="rounded-xl border border-border bg-surface p-4 transition hover:border-brand/20">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-foreground">{formatScreenEventKind(screenEvent.kind)}</p>
          <p className="mt-2 text-sm leading-6 text-foreground-muted">{screenEvent.summary}</p>
        </div>
        <div className="text-right">
          <p className="text-xs uppercase tracking-[0.16em] text-foreground-subtle">
            {formatFrameTimestamp(screenEvent.frameTimestampMs)}
          </p>
          <p className="mt-2 text-xs text-foreground-subtle">{formatTimestamp(screenEvent.recordedAt)}</p>
        </div>
      </div>
    </article>
  );
}
