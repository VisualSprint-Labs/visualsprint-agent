"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Clock, ChevronRight, Sparkles, LayoutList } from "lucide-react";

import { ErrorBanner } from "../../components/shared/error-banner";
import { StatusPill } from "../../components/ui/status-pill";
import { useMeetingSession } from "../meeting-session/context/meeting-session-provider";
import { CaptureReadiness } from "./components/capture-readiness";
import { CaptureStepper } from "./components/capture-stepper";
import { CreateMeetingForm } from "./components/create-meeting-form";

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
};

const rowItem = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3, ease: [0.16, 1, 0.3, 1] as const } },
};

export function MeetingSetupPage() {
  const { meeting, meetings, error, selectMeeting, capturePhase } = useMeetingSession();

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-8 px-4 py-6 sm:gap-10 sm:px-8 sm:py-10 lg:px-12">
      {/* Page header */}
      <motion.header
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] as const }}
        className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"
      >
        <div>
          <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-brand/20 bg-brand/5 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-brand">
            <Sparkles size={12} strokeWidth={2} />
            Setup
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-balance sm:text-4xl lg:text-5xl">
            Prepare your meeting
          </h1>
          <p className="mt-3 max-w-xl text-sm leading-7 text-foreground-muted sm:text-base">
            Create a session, verify browser capture support, then start the meeting to open the live workspace.
          </p>
        </div>
      </motion.header>

      {/* Main grid */}
      <div className="grid gap-8 xl:grid-cols-5">
        {/* Left column: forms */}
        <div className="xl:col-span-3 space-y-8">
          <CreateMeetingForm />

          <section>
            <p className="mb-4 text-xs font-semibold uppercase tracking-[0.2em] text-foreground-subtle">Pipeline</p>
            <CaptureStepper capturePhase={capturePhase} meeting={meeting} />
          </section>

          <CaptureReadiness />
        </div>

        {/* Right column: recent meetings sidebar */}
        <motion.div
          initial={{ opacity: 0, x: 16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] as const, delay: 0.2 }}
          className="xl:col-span-2"
        >
          <div className="sticky top-6 space-y-6">
            <div className="rounded-2xl border border-border bg-surface p-5 shadow-sm sm:p-6">
              <div className="flex items-center gap-3 mb-5">
                <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--accent-memory)]/10">
                  <Clock size={18} strokeWidth={2} className="text-[var(--accent-memory)]" />
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-foreground-subtle">Sessions</p>
                  <h2 className="text-lg font-bold tracking-tight">Recent meetings</h2>
                </div>
              </div>

              <motion.div
                variants={container}
                initial="hidden"
                animate="show"
                className="space-y-2"
              >
                {meetings.length === 0 ? (
                  <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-surface-muted/50 p-8 text-center">
                    <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-surface-2">
                      <LayoutList size={18} strokeWidth={2} className="text-foreground-subtle" />
                    </div>
                    <p className="text-sm font-semibold text-foreground">No meetings yet</p>
                    <p className="mt-1 text-xs text-foreground-muted">Create your first meeting to get started.</p>
                  </div>
                ) : (
                  meetings.map((item) => (
                    <motion.button
                      key={item.id}
                      variants={rowItem}
                      className={`group flex w-full items-center justify-between gap-3 rounded-xl border p-3.5 text-left transition-all duration-200 ${
                        meeting?.id === item.id
                          ? "border-brand bg-brand/5 shadow-sm ring-1 ring-brand/10"
                          : "border-border bg-surface-muted hover:border-border-strong hover:bg-surface hover:shadow-sm"
                      }`}
                      onClick={() => {
                        void selectMeeting(item.id);
                      }}
                      type="button"
                    >
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-foreground truncate">{item.title}</p>
                        <p className="mt-0.5 text-xs text-foreground-subtle">
                          {item.participantCount} participants
                        </p>
                      </div>
                      <StatusPill status={item.status} />
                    </motion.button>
                  ))
                )}
              </motion.div>

              {meeting ? (
                <div className="mt-5 pt-4 border-t border-border">
                  <Link
                    className="group/link inline-flex items-center gap-1.5 text-sm font-semibold text-brand transition hover:underline"
                    href={
                      meeting.status === "live"
                        ? `/meetings/${meeting.id}/live`
                        : meeting.status === "ended"
                          ? `/meetings/${meeting.id}/report`
                          : `/meetings/new`
                    }
                  >
                    Open selected meeting
                    <ChevronRight size={14} strokeWidth={2} className="transition group-hover/link:translate-x-0.5" />
                  </Link>
                </div>
              ) : null}
            </div>
          </div>
        </motion.div>
      </div>

      {error ? <ErrorBanner message={error} /> : null}
    </div>
  );
}
