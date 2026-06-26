"use client";

import type { OutcomeSearchResult, ReasoningRecordType } from "@visualsprint/contracts";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import {
  Search,
  Loader2,
  GitCommitHorizontal,
  CheckSquare,
  AlertTriangle,
  HelpCircle,
  BrainCircuit,
  ArrowUpRight,
  Database,
  User,
  Clock,
} from "lucide-react";

import { ThemeWrapper } from "../../components/layout/theme-wrapper";
import { EmptyState } from "../../components/ui/empty-state";
import { searchKnowledge } from "../../lib/api";
import { formatTimestamp } from "../../lib/format";

type Filter = "all" | ReasoningRecordType;

const filters: Array<{ id: Filter; label: string }> = [
  { id: "all", label: "All" },
  { id: "decision", label: "Decisions" },
  { id: "commitment", label: "Commitments" },
  { id: "blocker", label: "Blockers" },
  { id: "open_question", label: "Questions" },
];

const recordMeta: Record<
  ReasoningRecordType,
  { label: string; icon: typeof CheckSquare; className: string }
> = {
  decision: { label: "Decision", icon: CheckSquare, className: "bg-brand/12 text-brand" },
  commitment: {
    label: "Commitment",
    icon: GitCommitHorizontal,
    className: "bg-[var(--accent)]/12 text-[var(--accent)]",
  },
  blocker: {
    label: "Blocker",
    icon: AlertTriangle,
    className: "bg-[var(--status-error)]/12 text-[var(--status-error)]",
  },
  open_question: {
    label: "Question",
    icon: HelpCircle,
    className: "bg-[var(--accent-memory)]/12 text-[var(--accent-memory)]",
  },
};

function ResultCard({ result }: { result: OutcomeSearchResult }) {
  const meta = recordMeta[result.recordType];
  const Icon = meta.icon;
  return (
    <Link
      href={`/meetings/${result.meetingId}/report`}
      className="group flex flex-col gap-3 rounded-2xl border border-border bg-surface p-5 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-brand/30 hover:shadow-md"
    >
      <div className="flex items-center justify-between gap-2">
        <span
          className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold ${meta.className}`}
        >
          <Icon size={13} strokeWidth={2} />
          {meta.label}
        </span>
        <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-foreground-subtle">
          {result.status}
        </span>
      </div>

      <div>
        <p className="text-sm font-bold leading-6 text-foreground group-hover:text-brand">
          {result.summary}
        </p>
        <p className="mt-1 line-clamp-2 text-sm leading-6 text-foreground-muted">{result.detail}</p>
      </div>

      <div className="mt-auto flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-foreground-subtle">
        <span className="inline-flex items-center gap-1.5 font-medium text-foreground-muted">
          <ArrowUpRight size={12} strokeWidth={2} className="text-brand" />
          {result.meetingTitle}
        </span>
        {result.ownerLabel && result.ownerLabel !== "not mentioned" ? (
          <span className="inline-flex items-center gap-1.5">
            <User size={12} strokeWidth={2} />
            {result.ownerLabel}
          </span>
        ) : null}
        {result.dueHint ? <span>Due: {result.dueHint}</span> : null}
        {result.severity ? <span className="uppercase">{result.severity}</span> : null}
        <span className="inline-flex items-center gap-1.5">
          <Clock size={12} strokeWidth={2} />
          {formatTimestamp(result.updatedAt)}
        </span>
      </div>
    </Link>
  );
}

export function KnowledgeSearchPage() {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [results, setResults] = useState<OutcomeSearchResult[]>([]);
  const [available, setAvailable] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const [errored, setErrored] = useState(false);
  const requestIdRef = useRef(0);

  useEffect(() => {
    const handle = setTimeout(() => {
      const id = requestIdRef.current + 1;
      requestIdRef.current = id;
      setIsLoading(true);
      setErrored(false);
      void searchKnowledge({
        q: query.trim(),
        recordType: filter === "all" ? null : filter,
        limit: 30,
      })
        .then((response) => {
          if (requestIdRef.current !== id) return;
          setResults(response.results);
          setAvailable(response.available);
        })
        .catch(() => {
          if (requestIdRef.current !== id) return;
          setErrored(true);
          setResults([]);
        })
        .finally(() => {
          if (requestIdRef.current === id) setIsLoading(false);
        });
    }, 250);
    return () => clearTimeout(handle);
  }, [query, filter]);

  const heading = useMemo(
    () => (query.trim() ? "Search results" : "Recent across all meetings"),
    [query],
  );

  return (
    <ThemeWrapper theme="paper">
      <div className="mx-auto flex max-w-5xl flex-col gap-8 px-4 py-6 sm:gap-10 sm:px-8 sm:py-10 lg:px-12">
        <header>
          <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-brand/20 bg-brand/5 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-brand">
            <BrainCircuit size={12} strokeWidth={2} />
            Team knowledge
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-balance sm:text-4xl lg:text-5xl">
            Search past meetings
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-foreground-muted sm:text-base">
            Find decisions, commitments, blockers, and open questions from every meeting — so the
            team doesn&apos;t repeat discussions or lose context.
          </p>
        </header>

        {/* Search box */}
        <div className="space-y-4">
          <div className="relative">
            <Search
              size={18}
              strokeWidth={2}
              className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-foreground-subtle"
            />
            <input
              type="search"
              autoFocus
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search decisions, blockers, owners, topics…"
              aria-label="Search team knowledge"
              className="w-full rounded-2xl border border-border bg-surface py-3.5 pl-12 pr-4 text-base text-foreground shadow-sm outline-none transition focus:border-brand/40 focus:ring-2 focus:ring-brand/15"
            />
            {isLoading ? (
              <Loader2
                size={18}
                strokeWidth={2}
                className="absolute right-4 top-1/2 -translate-y-1/2 animate-spin text-foreground-subtle"
              />
            ) : null}
          </div>

          <div className="flex flex-wrap gap-2">
            {filters.map((item) => {
              const active = filter === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setFilter(item.id)}
                  className={`rounded-xl px-3.5 py-2 text-sm font-medium transition ${
                    active
                      ? "bg-brand/12 text-brand ring-1 ring-brand/15"
                      : "border border-border bg-surface text-foreground-muted hover:bg-surface-2 hover:text-foreground"
                  }`}
                >
                  {item.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Results */}
        {!available ? (
          <EmptyState
            title="Search isn't available yet"
            body="Connect Elasticsearch (write-back) so meeting outcomes are indexed and searchable across the team."
          />
        ) : errored ? (
          <EmptyState
            title="Couldn't run the search"
            body="Something went wrong reaching the knowledge index. Try again in a moment."
          />
        ) : isLoading && results.length === 0 ? (
          <div className="flex items-center justify-center gap-2 py-16 text-sm text-foreground-muted">
            <Loader2 size={16} strokeWidth={2} className="animate-spin" />
            Searching…
          </div>
        ) : results.length === 0 ? (
          <EmptyState
            title={query.trim() ? "No matches found" : "No meeting knowledge yet"}
            body={
              query.trim()
                ? "Try different words, or clear the filter to search all record types."
                : "Run and end a meeting to start building searchable team knowledge."
            }
          />
        ) : (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-foreground-subtle">
              <Database size={13} strokeWidth={2} />
              {heading} · {results.length}
            </div>
            <motion.div
              initial="hidden"
              animate="show"
              variants={{ hidden: {}, show: { transition: { staggerChildren: 0.03 } } }}
              className="grid gap-4 sm:grid-cols-2"
            >
              {results.map((result, i) => (
                <motion.div
                  key={`${result.meetingId}-${result.summary}-${i}`}
                  variants={{
                    hidden: { opacity: 0, y: 8 },
                    show: { opacity: 1, y: 0, transition: { duration: 0.25 } },
                  }}
                >
                  <ResultCard result={result} />
                </motion.div>
              ))}
            </motion.div>
          </div>
        )}
      </div>
    </ThemeWrapper>
  );
}
