"use client";

import type { ActionRecommendation } from "@visualsprint/contracts";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { motion } from "framer-motion";
import {
  CheckCircle2,
  XCircle,
  Zap,
  Ticket,
  MessageSquare,
  ListChecks,
  Sparkles,
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
      {recommendation.executionResult ? (
        <p className="mt-3 text-xs text-foreground-subtle">{recommendation.executionResult}</p>
      ) : null}
      <div className="mt-5 flex flex-wrap gap-2">
        {recommendation.status === "pending" ? (
          <>
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
              variant="secondary"
              leftIcon={<XCircle size={14} strokeWidth={2} />}
              disabled={isBusy}
              onClick={onReject}
            >
              Reject
            </Button>
          </>
        ) : null}
        {recommendation.status === "approved" ? (
          <Button
            size="sm"
            leftIcon={<Zap size={14} strokeWidth={2} />}
            disabled={isBusy}
            onClick={onExecute}
          >
            Execute
          </Button>
        ) : null}
      </div>
    </motion.article>
  );
}

export function ActionsPage() {
  const router = useRouter();
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

  if (!meeting) {
    return <PageSkeleton />;
  }

  if (meeting.status === "draft" || meeting.status === "live") {
    return <PageSkeleton />;
  }

  const pendingCount = actionRecommendations.filter(
    (item) => item.status === "pending",
  ).length;
  const approvedCount = actionRecommendations.filter(
    (item) => item.status === "approved",
  ).length;
  const completedCount = actionRecommendations.filter(
    (item) => item.status === "executed" || item.status === "failed",
  ).length;

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-8 px-4 py-6 sm:gap-10 sm:px-8 sm:py-10 lg:px-12">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-brand/20 bg-brand/5 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-brand">
            <ListChecks size={12} strokeWidth={2} />
            {meeting.title}
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-balance sm:text-4xl lg:text-5xl">
            Action recommendations
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-foreground-muted sm:text-base">
            Review Jira and Slack suggestions generated from the meeting report. Approve before
            execution.
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
          <Button
            variant="secondary"
            disabled={isBusy || meeting.status !== "ended"}
            leftIcon={<Sparkles size={16} strokeWidth={2} />}
            onClick={() => {
              void generateRecommendations();
            }}
          >
            Generate recommendations
          </Button>

          {actionRecommendations.length === 0 ? (
            <EmptyState
              title="No recommendations yet"
              body={
                meeting.status === "ended"
                  ? "Generate recommendations to see Jira and Slack suggestions."
                  : "End the meeting first to generate action recommendations."
              }
            />
          ) : (
            <motion.div
              variants={container}
              initial="hidden"
              animate="show"
              className="grid gap-3 sm:grid-cols-2"
            >
              {actionRecommendations.map((rec) => (
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
