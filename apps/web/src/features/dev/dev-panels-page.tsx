"use client";

import type { PlatformMetaResponse } from "@visualsprint/contracts";
import { Activity, Sprout } from "lucide-react";

import { Card } from "../../components/ui/card";
import { EmptyState } from "../../components/ui/empty-state";
import { InfoTile } from "../../components/ui/metric";
import { Button } from "../../components/ui/button";
import { ErrorBanner } from "../../components/shared/error-banner";
import { formatInvocationExecutionMode } from "../../lib/format";
import { getApiBaseUrl } from "../../lib/api";
import { useMeetingSession } from "../meeting-session/context/meeting-session-provider";

function DevJsonBlock({ value }: { value: unknown }) {
  return (
    <pre className="overflow-x-auto rounded-xl border border-border bg-surface-muted p-4 text-xs leading-6 text-foreground-muted">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

function DownstreamServiceCard({
  service,
}: {
  service: PlatformMetaResponse["downstreamServices"][number];
}) {
  return (
    <article className="rounded-xl border border-border bg-surface-muted p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-foreground">{service.service}</p>
          <p className="mt-1 text-xs uppercase tracking-[0.16em] text-foreground-muted">
            {service.kind} · {service.mode}
          </p>
        </div>
        <span className="rounded-lg bg-surface px-3 py-1 text-xs font-medium uppercase text-foreground-muted">
          {service.status}
        </span>
      </div>
      <p className="mt-2 text-sm leading-6 text-foreground-muted">{service.note}</p>
    </article>
  );
}

export function DevPanelsPage() {
  const {
    meeting,
    platformMeta,
    agentInvocationAudit,
    agentSmokeResult,
    isBusy,
    error,
    runAgentSmokeCheck,
    selectMeeting,
    meetings,
    chunkInsight,
    summaryPacket,
    indexedOutcomes,
    loadDemoMeeting,
  } = useMeetingSession();

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-8 px-6 py-10 sm:px-10">
      <header className="space-y-3">
        <p className="text-xs uppercase tracking-[0.24em] text-foreground-muted">Developer</p>
        <h1 className="text-4xl font-semibold tracking-tight text-balance">Integration tools</h1>
        <p className="text-sm text-foreground-muted">API base: {getApiBaseUrl()}</p>
      </header>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card title="Demo seed" eyebrow="Hackathon helper">
          <div className="space-y-4">
            <p className="text-sm leading-6 text-foreground-muted">
              Instantly create a fully populated demo meeting with transcript, screen events,
              decisions, blockers, memory matches, final report, and action recommendations.
            </p>
            <Button
              leftIcon={<Sprout size={16} strokeWidth={2} />}
              disabled={isBusy}
              onClick={() => {
                void loadDemoMeeting();
              }}
            >
              Load demo meeting
            </Button>
            {meeting ? (
              <p className="text-sm text-foreground-muted">
                Selected: <span className="font-medium text-foreground">{meeting.title}</span>
              </p>
            ) : null}
          </div>
        </Card>

        <Card title="Platform topology" eyebrow="Service boundaries">
          {platformMeta ? (
            <div className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <InfoTile label="Memory layer" value={platformMeta.memoryIntegration.provider} />
                <InfoTile
                  label="Outcome index"
                  value={platformMeta.memoryIntegration.outcomesIndex ?? "not set"}
                />
              </div>
              {platformMeta.downstreamServices.map((service) => (
                <DownstreamServiceCard key={service.kind} service={service} />
              ))}
            </div>
          ) : (
            <EmptyState title="No platform meta" body="Platform metadata has not loaded yet." />
          )}
        </Card>

        <Card title="Agent smoke check" eyebrow="Adapter runtime">
          <div className="space-y-4">
            <Button
              leftIcon={<Activity size={16} strokeWidth={2} />}
              disabled={isBusy || !meeting}
              onClick={() => {
                void runAgentSmokeCheck();
              }}
            >
              Run agent smoke
            </Button>
            {agentSmokeResult ? (
              <p className="text-sm text-foreground-muted">
                {agentSmokeResult.reasoning.note} · {agentSmokeResult.summary.note}
              </p>
            ) : (
              <EmptyState title="No smoke run yet" body="Run smoke to test the agents seam." />
            )}
          </div>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card title="Chunk insight" eyebrow="Latest processed segment">
          {chunkInsight ? (
            <div className="space-y-4">
              <p className="text-sm leading-7 text-foreground-muted">{chunkInsight.focusSummary}</p>
              <div className="grid gap-3 sm:grid-cols-2">
                <InfoTile label="Client chunk" value={chunkInsight.clientChunkId} />
                <InfoTile label="Attention flags" value={String(chunkInsight.attentionFlags.length)} />
              </div>
              {chunkInsight.focusAreas.length > 0 ? (
                <div className="space-y-2">
                  {chunkInsight.focusAreas.map((area) => (
                    <article
                      key={`${area.recordType}-${area.summary}`}
                      className="rounded-xl border border-border bg-surface-muted p-3"
                    >
                      <p className="text-xs uppercase tracking-[0.16em] text-foreground-muted">
                        {area.recordType.replace(/_/g, " ")}
                      </p>
                      <p className="mt-1 text-sm font-semibold text-foreground">{area.summary}</p>
                      <p className="mt-1 text-sm text-foreground-muted">{area.detail}</p>
                    </article>
                  ))}
                </div>
              ) : null}
              <DevJsonBlock value={chunkInsight.reasoningChecklist} />
            </div>
          ) : (
            <EmptyState
              title="No chunk insight"
              body="Process at least one capture segment during a live meeting to inspect reasoning focus."
            />
          )}
        </Card>

        <Card title="Summary packet" eyebrow="Draft report assembly">
          {summaryPacket ? (
            <div className="space-y-4">
              <p className="text-sm leading-7 text-foreground-muted">
                {summaryPacket.draftExecutiveSummary || "No executive summary drafted yet."}
              </p>
              <div className="grid gap-3 sm:grid-cols-2">
                <InfoTile label="Decisions" value={String(summaryPacket.decisions.length)} />
                <InfoTile label="Commitments" value={String(summaryPacket.commitments.length)} />
                <InfoTile label="Blockers" value={String(summaryPacket.blockers.length)} />
                <InfoTile label="Memory highlights" value={String(summaryPacket.memoryHighlights.length)} />
              </div>
              {summaryPacket.reportChecklist.length > 0 ? (
                <ul className="list-disc space-y-1 pl-5 text-sm text-foreground-muted">
                  {summaryPacket.reportChecklist.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : (
            <EmptyState
              title="No summary packet"
              body="Summary packets populate as live signals arrive during an active meeting."
            />
          )}
        </Card>
      </div>

      <Card title="Indexed outcomes" eyebrow="Elastic memory preview">
        {indexedOutcomes.length > 0 ? (
          <div className="space-y-3">
            {indexedOutcomes.slice(0, 12).map((outcome) => (
              <article
                key={outcome.id}
                className="rounded-xl border border-border bg-surface-muted p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-foreground">{outcome.summary}</p>
                  <span className="rounded-lg bg-surface px-2 py-0.5 text-xs uppercase text-foreground-muted">
                    {outcome.recordType.replace(/_/g, " ")}
                  </span>
                </div>
                <p className="mt-2 text-sm text-foreground-muted">{outcome.detail}</p>
                <p className="mt-2 text-xs text-foreground-muted">
                  {outcome.status} · updated {outcome.updatedAt}
                </p>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No indexed outcomes"
            body="Outcome documents appear after reasoning records are indexed for this meeting."
          />
        )}
      </Card>

      <Card title="Agent invocation audit" eyebrow="Recent runs">
        {agentInvocationAudit?.summary.available ? (
          <div className="space-y-3">
            {agentInvocationAudit.invocations.slice(0, 8).map((invocation) => (
              <article
                key={`${invocation.agentKind}-${invocation.requestKey}-${invocation.invokedAt}`}
                className="rounded-xl border border-border bg-surface-muted p-4"
              >
                <p className="text-sm font-semibold text-foreground">
                  {invocation.agentKind} · {formatInvocationExecutionMode(invocation.executionMode)}
                </p>
                <p className="mt-2 text-sm text-foreground-muted">{invocation.detail}</p>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState title="Audit unavailable" body="Adapter audit proxy is not reachable." />
        )}
      </Card>

      <Card title="Meeting selector" eyebrow="Debug">
        <div className="flex flex-wrap gap-2">
          {meetings.map((item) => (
            <Button
              key={item.id}
              variant="secondary"
              size="sm"
              onClick={() => {
                void selectMeeting(item.id);
              }}
            >
              {item.title}
            </Button>
          ))}
        </div>
      </Card>

      {error ? <ErrorBanner message={error} /> : null}
    </div>
  );
}
