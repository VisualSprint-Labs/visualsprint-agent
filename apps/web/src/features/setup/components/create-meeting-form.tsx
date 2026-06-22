"use client";

import { sourceConnectors } from "@visualsprint/contracts";
import type { CreateMeetingRequest } from "@visualsprint/contracts";
import { useRouter } from "next/navigation";
import { Play } from "lucide-react";

import { Card } from "../../../components/ui/card";
import { Field } from "../../../components/ui/field";
import { inputClassName } from "../../../components/ui/button-styles";
import { Button } from "../../../components/ui/button";
import { useMeetingSession } from "../../meeting-session/context/meeting-session-provider";

export function CreateMeetingForm() {
  const router = useRouter();
  const { draft, setDraft, isBusy, createMeetingFromDraft, startMeetingSession } =
    useMeetingSession();

  // One action: create the meeting, start it, and drop the user straight into the
  // live workspace — no separate "now start it" step to discover.
  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const created = await createMeetingFromDraft(event);
    if (!created) {
      return;
    }
    await startMeetingSession(created.id);
    // Draft /live redirects back to setup, so this is safe even if start failed
    // (the error toast will have surfaced the reason).
    router.push(`/meetings/${created.id}/live`);
  }

  return (
    <Card title="Create meeting" eyebrow="Configuration">
      <form className="space-y-6" onSubmit={handleSubmit}>
        <Field label="Meeting title">
          <input
            aria-label="Meeting title"
            className={inputClassName}
            placeholder="Weekly product sync"
            value={draft.title}
            onChange={(event) =>
              setDraft((current: CreateMeetingRequest) => ({
                ...current,
                title: event.target.value,
              }))
            }
          />
        </Field>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Participant count">
            <input
              aria-label="Participant count"
              className={inputClassName}
              min={1}
              max={50}
              placeholder="4"
              type="number"
              value={draft.participantCount}
              onChange={(event) =>
                setDraft((current: CreateMeetingRequest) => ({
                  ...current,
                  participantCount: Number(event.target.value) || 1,
                }))
              }
            />
          </Field>

          <Field label="Primary connector">
            <select
              aria-label="Primary connector"
              className={inputClassName}
              title="Primary connector"
              value={draft.sourceConnector}
              onChange={(event) =>
                setDraft((current: CreateMeetingRequest) => ({
                  ...current,
                  sourceConnector: event.target.value as CreateMeetingRequest["sourceConnector"],
                }))
              }
            >
              {sourceConnectors.map((connector) => (
                <option
                  key={connector.slug}
                  disabled={connector.slug !== "browser_live_capture"}
                  value={connector.slug}
                >
                  {connector.label}
                  {connector.slug !== "browser_live_capture" ? " (planned)" : ""}
                </option>
              ))}
            </select>
          </Field>
        </div>

        <Field label="Meeting notes">
          <textarea
            aria-label="Meeting notes"
            className={`${inputClassName} min-h-28 resize-y`}
            placeholder="Context, goals, and decisions to capture"
            value={draft.notes}
            onChange={(event) =>
              setDraft((current: CreateMeetingRequest) => ({
                ...current,
                notes: event.target.value,
              }))
            }
          />
        </Field>

        <div className="flex flex-col gap-2 pt-2">
          <Button
            leftIcon={<Play size={16} strokeWidth={2.5} />}
            disabled={isBusy}
            type="submit"
            size="lg"
            className="shadow-sm"
          >
            {isBusy ? "Starting…" : "Create & start meeting"}
          </Button>
          <p className="text-xs text-foreground-muted">
            We&apos;ll open the live workspace and ask which screen or tab to share.
          </p>
        </div>
      </form>
    </Card>
  );
}
