"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { motion } from "framer-motion";
import { ArrowLeft, FileText, RotateCcw } from "lucide-react";

import { ErrorBanner } from "../../components/shared/error-banner";
import { PageGuide } from "../../components/shared/page-guide";
import { EmptyState } from "../../components/ui/empty-state";
import { PageSkeleton } from "../../components/ui/skeleton";
import { Button } from "../../components/ui/button";
import { useMeetingSession } from "../meeting-session/context/meeting-session-provider";
import { FinalReportView } from "./components/final-report-view";

export function MeetingReportPage() {
  const router = useRouter();
  const { meeting, finalReport, error, isBusy, actionRecommendations, refreshFinalReport } =
    useMeetingSession();

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

  const reportReady =
    meeting.status === "ended" && finalReport?.meetingId === meeting.id ? finalReport : null;
  const isGenerating = meeting.status === "ended" && !reportReady;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] as const }}
      className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-6 sm:gap-8 sm:px-8 sm:py-10 lg:px-12"
    >
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-brand/20 bg-brand/5 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-brand">
            <FileText size={12} strokeWidth={2} />
            {meeting.title}
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-balance sm:text-4xl lg:text-5xl">
            Meeting report
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-foreground-muted sm:text-base">
            The evidence-backed system of record for what was decided, who owns follow-up, and
            what organizational memory applies.
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/meetings">
            <Button variant="ghost" size="sm" leftIcon={<ArrowLeft size={14} strokeWidth={2} />}>
              Back
            </Button>
          </Link>
        </div>
      </header>

      {reportReady ? (
        <>
          <PageGuide
            icon={<FileText size={18} strokeWidth={2.5} />}
            eyebrow="Your report"
            title="This is the meeting's system of record"
            body="Every decision, commitment, blocker, and open question below was pulled from what actually happened — the screen and the conversation. Click any evidence link on a card to jump straight to the moment it came from."
            action={{
              label: "Turn these into Jira tickets & Slack messages",
              href: `/meetings/${meeting.id}/actions`,
            }}
          />
          <FinalReportView
            hasRecommendations={actionRecommendations.length > 0}
            meetingId={meeting.id}
            report={reportReady}
            screenEvents={meeting.recentScreenEvents}
            transcriptSegments={meeting.recentTranscriptSegments}
          />
        </>
      ) : isGenerating ? (
        <div className="space-y-4">
          <PageSkeleton />
          <div className="flex flex-wrap items-center gap-3">
            <p className="text-sm text-foreground-muted">Generating the final report…</p>
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<RotateCcw size={14} strokeWidth={2} />}
              disabled={isBusy}
              onClick={() => {
                void refreshFinalReport();
              }}
            >
              {isBusy ? "Retrying…" : "Retry generation"}
            </Button>
          </div>
        </div>
      ) : (
        <EmptyState
          title="Report not ready"
          body="End the meeting to generate the evidence-backed report."
        />
      )}

      {error ? <ErrorBanner message={error} /> : null}
    </motion.div>
  );
}
