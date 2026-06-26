"use client";

import type { ActionRecommendation, ActionRecommendationStatus } from "@visualsprint/contracts";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  CheckCircle2,
  XCircle,
  Zap,
  Ticket,
  MessageSquare,
  ListChecks,
  Sparkles,
  Clock,
  PlayCircle,
} from "lucide-react";

import { Card } from "../../components/ui/card";
import { EmptyState } from "../../components/ui/empty-state";
import { InfoTile } from "../../components/ui/metric";
import { PageSkeleton } from "../../components/ui/skeleton";
import { Button } from "../../components/ui/button";
import { ErrorBanner } from "../../components/shared/error-banner";
import { PageGuide } from "../../components/shared/page-guide";
import { useMeetingSession } from "../meeting-session/context/meeting-session-provider";

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.04 } },
};

const cardItem = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: 0.25, ease: [0.16, 1, 0.3, 1] as const } },
};

type FilterTab = "pending" | "approved" | "completed" | "all";

const filterTabs: Array<{ id: FilterTab; label: string; icon: typeof Clock; match: (status: ActionRecommendationStatus) => boolean }> = [
  { id: "pending", label: "Pending", icon: Clock, match: (s) => s === "pending" },
  { id: "approved", label: "Approved", icon: CheckCircle2, match: (s) => s === "approved" },
  { id: "completed", label: "Completed", icon: PlayCircle, match: (s) => s === "executed" || s === "failed" || s === "rejected" },
  { id: "all", label: "All", icon: ListChecks, match: () => true },
];

function RecommendationCard({
  recommendation,
  isBusy,
  onApprove,
  onReject,
  onExecute,
}: {
  recommendation: ActionRecommendation;
  isBusy: boolean;
  onApprove: () => void;
  onReject: () => void;
  onExecute: () => void;
}) {
  const isJira = recommendation.type.startsWith("jira_");
  const typeIcon = isJira ? (
    <Ticket size={14} strokeWidth={2} />
  ) : (
    <MessageSquare size={14} strokeWidth={2} />
  );

  const typeLabel = recommendation.type.replace(/_/g, " ");
  const title =
    recommendation.jiraDetails?.title ??
    recommendation.slackDetails?.title ??
    "Untitled";
  const description =
    recommendation.jiraDetails?.description ??
    recommendation.slackDetails?.message ??
    "";
  const target = isJira
    ? "Jira"
    : recommendation.slackDetails?.channel && recommendation.slackDetails.channel !== "not specified"
      ? `Slack ${recommendation.slackDetails.channel}`
      : "Slack";
  const executeLabel = isJira ? "Create Jira issue" : "Send to Slack";
  const evidence =
    recommendation.jiraDetails?.evidence ??
    recommendation.slackDetails?.evidence ??
    recommendation.evidence ??
    [];

  return (
    <motion.article
      variants={cardItem}
      className="group relative overflow-hidden rounded-2xl border border-border bg-surface p-5 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-brand/20 hover:shadow-lg"
    >
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-brand/20 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-surface-muted px-2.5 py-1 text-xs font-medium text-foreground-muted">
            {typeIcon}
            {typeLabel}
          </span>
          <span
            className={`rounded-lg px-2.5 py-1 text-xs font-bold uppercase tracking-[0.1em] ${
              recommendation.status === "pending"
                ? "bg-[var(--status-draft)]/15 text-[var(--status-draft)]"
                : recommendation.status === "approved"
                  ? "bg-[var(--status-live)]/15 text-[var(--status-live)]"
                  : recommendation.status === "executed"
                    ? "bg-[var(--status-success)]/15 text-[var(--status-success)]"
                    : "bg-surface-muted text-foreground-muted"
            }`}
          >
            {recommendation.status}
          </span>
          <span className="rounded-lg bg-surface-muted px-2.5 py-1 text-xs font-bold uppercase tracking-[0.1em] text-[var(--status-draft)]">
            {recommendation.urgency}
          </span>
        </div>
        <span className="text-xs font-medium text-foreground-subtle">
          {(recommendation.confidence * 100).toFixed(0)}% confidence
        </span>
      </div>
      <p className="mt-4 text-sm font-bold text-foreground">{title}</p>
      <p className="mt-1.5 text-sm leading-6 text-foreground-muted">{description}</p>

      <p className="mt-3 inline-flex items-center gap-1.5 text-xs text-foreground-subtle">
        {isJira ? <Ticket size={12} strokeWidth={2} /> : <MessageSquare size={12} strokeWidth={2} />}
        Will be created in {target} after you approve and execute
      </p>

      {evidence.length > 0 ? (
        <div className="mt-3 rounded-lg border border-border bg-surface-muted/60 p-3">
          <p className="mb-1 text-[10px] font-bold uppercase tracking-[0.14em] text-foreground-subtle">
            From the meeting
          </p>
          <ul className="space-y-1">
            {evidence.slice(0, 2).map((ref, i) => (
              <li key={i} className="text-xs leading-5 text-foreground-muted">
                {ref.note || ref.transcriptRef || "Linked meeting moment"}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {recommendation.executionResult ? (
        <p className="mt-3 rounded-lg bg-surface-muted/60 px-3 py-2 text-xs text-foreground-subtle">
          {recommendation.executionResult}
        </p>
      ) : null}

      <div className="mt-5 border-t border-border pt-4">
        {recommendation.status === "pending" ? (
          <div className="flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              leftIcon={<CheckCircle2 size={14} strokeWidth={2} />}
              disabled={isBusy}
              onClick={onApprove}
            >
              Approve
            </Button>
            <Button
              size="sm"
              variant="ghost"
              leftIcon={<XCircle size={14} strokeWidth={2} />}
              disabled={isBusy}
              onClick={onReject}
            >
              Reject
            </Button>
            <span className="ml-auto text-xs text-foreground-subtle">Step 1 of 2 · nothing sent yet</span>
          </div>
        ) : recommendation.status === "approved" ? (
          <div className="flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              leftIcon={<Zap size={14} strokeWidth={2} />}
              disabled={isBusy}
              onClick={onExecute}
            >
              {executeLabel}
            </Button>
            <span className="ml-auto text-xs text-foreground-subtle">
              Approved · this will send it now
            </span>
          </div>
        ) : (
          <p className="text-xs font-medium text-foreground-muted">
            {recommendation.status === "executed"
              ? `Sent to ${target}.`
              : recommendation.status === "rejected"
                ? "Rejected — not sent."
                : "Could not be sent."}
          </p>
        )}
      </div>
    </motion.article>
  );
}

export function ActionsPage() {
  const router = useRouter();
  const [activeFilter, setActiveFilter] = useState<FilterTab>("pending");
  const {
    meeting,
    actionRecommendations,
    isBusy,
    error,
    generateRecommendations,
    approveRecommendation,
    rejectRecommendation,
    executeRecommendation,
  } = useMeetingSession();

  useEffect(() => {
    if (!meeting) {
      return;
    }
    if (meeting.status === "draft") {
      router.replace(`/meetings/new?meetingId=${meeting.id}`);
      return;
    }
    if (meeting.status === "live") {
      router.replace(`/meetings/${meeting.id}/live`);
    }
  }, [meeting, router]);

  const pendingCount = actionRecommendations.filter((item) => item.status === "pending").length;
  const approvedCount = actionRecommendations.filter((item) => item.status === "approved").length;
  const completedCount = actionRecommendations.filter(
    (item) => item.status === "executed" || item.status === "failed" || item.status === "rejected",
  ).length;

  const filteredRecommendations = useMemo(() => {
    const tab = filterTabs.find((t) => t.id === activeFilter);
    return actionRecommendations.filter((rec) => tab?.match(rec.status));
  }, [actionRecommendations, activeFilter]);

  if (!meeting) {
    return <PageSkeleton />;
  }

  if (meeting.status === "draft" || meeting.status === "live") {
    return <PageSkeleton />;
  }

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-8 px-4 py-6 sm:gap-10 sm:px-8 sm:py-10 lg:px-12">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-brand/20 bg-brand/5 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-brand">
            <ListChecks size={12} strokeWidth={2} />
            {meeting.title}
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-balance sm:text-4xl lg:text-5xl">Action recommendations</h1>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-foreground-muted sm:text-base">
            Review Jira and Slack suggestions generated from the meeting report. Approve before execution.
          </p>
        </div>
      </header>

      <PageGuide
        icon={<ListChecks size={18} strokeWidth={2.5} />}
        eyebrow="How approval works"
        title="Nothing is sent until you approve it"
        body="These are AI-drafted suggestions based on your meeting report — they have not touched Jira or Slack yet. Review each card, approve the ones you want, then execute to actually create the ticket or post the message."
        steps={[
          { label: "Review", body: "Read each suggested Jira ticket or Slack message and its confidence." },
          { label: "Approve or reject", body: "Keep the ones you want; reject anything you don't need." },
          { label: "Execute", body: "Send approved items to Jira or Slack — only then do they go live." },
        ]}
      />

      {actionRecommendations.length > 0 ? (
        <div className="grid gap-3 sm:grid-cols-3">
          <InfoTile label="Pending review" value={String(pendingCount)} />
          <InfoTile label="Approved" value={String(approvedCount)} />
          <InfoTile label="Completed" value={String(completedCount)} />
        </div>
      ) : null}

      <Card title="Approval portal" eyebrow="Post-meeting actions">
        <div className="space-y-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-wrap gap-2">
              {filterTabs.map((tab) => {
                const active = activeFilter === tab.id;
                const Icon = tab.icon;
                const count = actionRecommendations.filter((rec) => tab.match(rec.status)).length;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setActiveFilter(tab.id)}
                    className={`inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition-all duration-200 ${
                      active
                        ? "bg-brand/10 text-brand shadow-sm ring-1 ring-brand/10"
                        : "border border-border bg-surface text-foreground-muted hover:text-foreground hover:bg-surface-2"
                    }`}
                  >
                    <Icon size={14} strokeWidth={2} />
                    {tab.label}
                    <span className={`ml-1 rounded-md px-1.5 py-0.5 text-[10px] font-bold ${active ? "bg-brand/20" : "bg-surface-muted"}`}>
                      {count}
                    </span>
                  </button>
                );
              })}
            </div>
            <Button
              variant="secondary"
              disabled={isBusy || meeting.status !== "ended"}
              leftIcon={<Sparkles size={16} strokeWidth={2} />}
              onClick={() => {
                void generateRecommendations();
              }}
            >
              Generate
            </Button>
          </div>

          {actionRecommendations.length === 0 ? (
            <EmptyState
              title="No recommendations yet"
              body={
                meeting.status === "ended"
                  ? "Generate recommendations after the report is ready to see Jira and Slack suggestions you can approve."
                  : "End the meeting first, then generate recommendations once the report is ready."
              }
            />
          ) : filteredRecommendations.length === 0 ? (
            <EmptyState title={`No ${activeFilter} recommendations`} body="Try another filter or generate new recommendations." />
          ) : (
            <motion.div variants={container} initial="hidden" animate="show" className="grid gap-3 sm:grid-cols-2">
              {filteredRecommendations.map((rec) => (
                <RecommendationCard
                  key={rec.id}
                  isBusy={isBusy}
                  onApprove={() => {
                    void approveRecommendation(rec.id);
                  }}
                  onExecute={() => {
                    void executeRecommendation(rec.id);
                  }}
                  onReject={() => {
                    void rejectRecommendation(rec.id);
                  }}
                  recommendation={rec}
                />
              ))}
            </motion.div>
          )}
        </div>
      </Card>

      {error ? <ErrorBanner message={error} /> : null}
    </div>
  );
}
