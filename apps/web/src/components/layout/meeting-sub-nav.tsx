"use client";

import { Fragment } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight } from "lucide-react";

import { useMeetingSession } from "../../features/meeting-session/context/meeting-session-provider";

const sections = [
  { suffix: "live", label: "Live", hint: "Capture & watch insights", liveOnly: true },
  { suffix: "report", label: "Report", hint: "Evidence-backed summary", liveOnly: false },
  { suffix: "actions", label: "Actions", hint: "Approve Jira & Slack", liveOnly: false },
] as const;

export function MeetingSubNav({ meetingId }: { meetingId?: string }) {
  const pathname = usePathname();
  const { meeting } = useMeetingSession();

  if (!meetingId) {
    return null;
  }

  const isLive = meeting?.status === "live";
  const visibleSections = sections.filter((section) => isLive || !section.liveOnly);

  return (
    <nav
      aria-label="Meeting stages"
      className="border-b border-border bg-[var(--bg-elevated)]/80"
    >
      <div className="mx-auto flex max-w-7xl items-center gap-1 overflow-x-auto px-4 py-2.5 sm:px-8 lg:px-10">
        {visibleSections.map((section, i) => {
          const href = `/meetings/${meetingId}/${section.suffix}`;
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Fragment key={section.suffix}>
              {i > 0 ? (
                <ChevronRight
                  size={15}
                  strokeWidth={2}
                  className="shrink-0 text-foreground-subtle"
                  aria-hidden
                />
              ) : null}
              <Link
                href={href}
                aria-current={active ? "page" : undefined}
                className={`group flex shrink-0 items-center gap-2.5 rounded-full py-1.5 pl-1.5 pr-3.5 transition ${
                  active
                    ? "bg-brand/12 ring-1 ring-brand/20"
                    : "hover:bg-surface-2"
                }`}
              >
                <span
                  className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-bold transition ${
                    active
                      ? "bg-brand text-brand-fg"
                      : "bg-surface-2 text-foreground-subtle group-hover:text-foreground"
                  }`}
                >
                  {i + 1}
                </span>
                <span className="flex flex-col leading-tight">
                  <span
                    className={`text-sm font-semibold ${
                      active ? "text-brand" : "text-foreground-muted group-hover:text-foreground"
                    }`}
                  >
                    {section.label}
                  </span>
                  <span className="hidden text-[11px] text-foreground-subtle sm:block">
                    {section.hint}
                  </span>
                </span>
              </Link>
            </Fragment>
          );
        })}
      </div>
    </nav>
  );
}
