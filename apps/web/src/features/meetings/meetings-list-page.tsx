"use client";

import type { MeetingStatus, MeetingSummary } from "@visualsprint/contracts";
import Link from "next/link";
import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { LayoutList, PlusCircle, Radio, Clock, CheckCircle2, ChevronRight, Users, Calendar, Monitor, Mic, FileText } from "lucide-react";

import { ThemeWrapper } from "../../components/layout/theme-wrapper";
import { Button } from "../../components/ui/button";
import { EmptyState } from "../../components/ui/empty-state";
import { PageSkeleton } from "../../components/ui/skeleton";
import { StatusPill } from "../../components/ui/status-pill";
import { useMeetings } from "../../hooks/use-meetings";
import { formatSourceConnector, formatTimestamp } from "../../lib/format";
import { meetingRouteForStatus } from "../../lib/meeting";

const statusFilters: Array<{ id: MeetingStatus | "all"; label: string; icon: typeof LayoutList; count?: number }> = [
  { id: "all", label: "All", icon: LayoutList },
  { id: "draft", label: "Draft", icon: Clock },
  { id: "live", label: "Live", icon: Radio },
  { id: "ended", label: "Ended", icon: CheckCircle2 },
];

const statusRank: Record<MeetingStatus, number> = {
  live: 0,
  draft: 1,
  ended: 2,
};

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.04 } },
};

const rowItem = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: 0.25, ease: [0.16, 1, 0.3, 1] as const } },
};

function MeetingRow({ meeting }: { meeting: MeetingSummary }) {
  return (
    <Link
      href={meetingRouteForStatus(meeting)}
      className="group flex items-center gap-4 rounded-xl border border-border bg-surface p-4 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-brand/20 hover:bg-surface-2 hover:shadow-md sm:gap-6 sm:p-5"
    >
      <div className="hidden shrink-0 sm:block">
        <div
          className={`inline-flex h-10 w-10 items-center justify-center rounded-lg ${
            meeting.status === "live"
              ? "bg-[var(--status-live)]/10 text-[var(--status-live)]"
              : meeting.status === "ended"
                ? "bg-surface-muted text-foreground-muted"
                : "bg-[var(--status-draft)]/10 text-[var(--status-draft)]"
          }`}
        >
          {meeting.status === "live" ? (
            <Radio size={18} strokeWidth={2} />
          ) : meeting.status === "ended" ? (
            <CheckCircle2 size={18} strokeWidth={2} />
          ) : (
            <Clock size={18} strokeWidth={2} />
          )}
        </div>
      </div>

      <div className="min-w-0 flex-1">
        <h2 className="truncate text-sm font-semibold text-foreground transition group-hover:text-brand sm:text-base">
          {meeting.title}
        </h2>
        <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-foreground-subtle">
          <span className="inline-flex items-center gap-1.5">
            <Users size={12} strokeWidth={2} />
            {meeting.participantCount} participants
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Calendar size={12} strokeWidth={2} />
            {formatTimestamp(meeting.createdAt)}
          </span>
          <span className="hidden sm:inline">{formatSourceConnector(meeting.sourceConnector)}</span>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-3">
        <StatusPill status={meeting.status} />
        <ChevronRight
          size={18}
          strokeWidth={2}
          className="text-foreground-subtle transition group-hover:translate-x-0.5 group-hover:text-brand"
        />
      </div>
    </Link>
  );
}

export function MeetingsListPage() {
  const [statusFilter, setStatusFilter] = useState<MeetingStatus | "all">("all");
  const { data, isLoading, error } = useMeetings();
  const meetings = useMemo(() => data?.meetings ?? [], [data?.meetings]);

  const counts = useMemo(() => {
    return {
      all: meetings.length,
      draft: meetings.filter((m) => m.status === "draft").length,
      live: meetings.filter((m) => m.status === "live").length,
      ended: meetings.filter((m) => m.status === "ended").length,
    };
  }, [meetings]);

  const filteredMeetings = useMemo(
    () =>
      (statusFilter === "all"
        ? meetings
        : meetings.filter((meeting) => meeting.status === statusFilter)
      ).slice().sort((a, b) => statusRank[a.status] - statusRank[b.status] || b.createdAt.localeCompare(a.createdAt)),
    [meetings, statusFilter],
  );

  return (
    <ThemeWrapper theme="paper">
      <div className="mx-auto flex max-w-5xl flex-col gap-8 px-4 py-6 sm:gap-10 sm:px-8 sm:py-10 lg:px-12">
        {/* Header */}
        <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-brand/20 bg-brand/5 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-brand">
              <LayoutList size={12} strokeWidth={2} />
              Workspace
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-balance sm:text-4xl lg:text-5xl">Meetings</h1>
            <p className="mt-3 max-w-xl text-sm leading-7 text-foreground-muted sm:text-base">
              Resume a live session or open the evidence-backed report from a completed meeting.
            </p>
          </div>
          <Link href="/meetings/new">
            <Button leftIcon={<PlusCircle size={16} strokeWidth={2} />} className="shadow-sm">
              New meeting
            </Button>
          </Link>
        </div>

        {/* Filters */}
        {!isLoading && !error && meetings.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {statusFilters.map((filter) => {
              const active = statusFilter === filter.id;
              const Icon = filter.icon;
              const count = counts[filter.id];
              return (
                <button
                  key={filter.id}
                  className={`inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-all duration-200 ${
                    active
                      ? "bg-brand/10 text-brand shadow-sm ring-1 ring-brand/10"
                      : "border border-border bg-surface text-foreground-muted hover:text-foreground hover:bg-surface-2 hover:shadow-sm"
                  }`}
                  onClick={() => setStatusFilter(filter.id)}
                  type="button"
                >
                  <Icon size={14} strokeWidth={2} />
                  {filter.label}
                  {typeof count === "number" ? (
                    <span className={`ml-1 rounded-md px-1.5 py-0.5 text-[10px] font-bold ${active ? "bg-brand/20" : "bg-surface-muted"}`}>
                      {count}
                    </span>
                  ) : null}
                </button>
              );
            })}
          </div>
        ) : null}

        {/* Content */}
        {isLoading ? (
          <PageSkeleton />
        ) : error ? (
          <EmptyState title="Unable to load meetings" body={String(error)} />
        ) : meetings.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] as const }}
            className="overflow-hidden rounded-3xl border border-brand/20 bg-gradient-to-b from-brand/[0.06] to-transparent p-8 sm:p-12"
          >
            <div className="mx-auto max-w-2xl text-center">
              <div className="mx-auto mb-5 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-brand/12 text-brand">
                <Radio size={26} strokeWidth={2} />
              </div>
              <h2 className="text-balance text-2xl font-bold tracking-tight sm:text-3xl">
                Run your first meeting with VisualSprint
              </h2>
              <p className="mx-auto mt-3 max-w-lg text-sm leading-7 text-foreground-muted sm:text-base">
                Share your screen and talk through a meeting — an AI agent watches and listens, then
                hands you the decisions, blockers, and ready-to-send Jira &amp; Slack actions.
              </p>

              <div className="mx-auto mt-8 grid max-w-xl gap-3 sm:grid-cols-3">
                {[
                  { icon: Monitor, label: "Capture", body: "Share a screen or tab to start." },
                  { icon: Mic, label: "Run it", body: "Insights appear as you talk." },
                  { icon: FileText, label: "Report", body: "Summary + actions at the end." },
                ].map((step, i) => {
                  const Icon = step.icon;
                  return (
                    <div
                      key={step.label}
                      className="rounded-2xl border border-border bg-surface/70 p-4 text-left"
                    >
                      <div className="mb-2 flex items-center gap-2">
                        <span className="inline-flex h-6 w-6 items-center justify-center rounded-lg bg-brand/10 text-[11px] font-bold text-brand">
                          {i + 1}
                        </span>
                        <Icon size={15} strokeWidth={2} className="text-brand" />
                        <span className="text-sm font-semibold">{step.label}</span>
                      </div>
                      <p className="text-xs leading-5 text-foreground-muted">{step.body}</p>
                    </div>
                  );
                })}
              </div>

              <div className="mt-8">
                <Link href="/meetings/new">
                  <Button size="lg" leftIcon={<PlusCircle size={18} strokeWidth={2.5} />} className="shadow-sm">
                    Create your first meeting
                  </Button>
                </Link>
              </div>
            </div>
          </motion.div>
        ) : filteredMeetings.length === 0 ? (
          <EmptyState
            title={`No ${statusFilter} meetings`}
            body="Try another filter or create a new meeting."
          />
        ) : (
          <motion.div variants={container} initial="hidden" animate="show" className="flex flex-col gap-3">
            {filteredMeetings.map((meeting) => (
              <motion.div key={meeting.id} variants={rowItem}>
                <MeetingRow meeting={meeting} />
              </motion.div>
            ))}
          </motion.div>
        )}
      </div>
    </ThemeWrapper>
  );
}
