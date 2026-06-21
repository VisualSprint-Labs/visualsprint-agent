"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import type { ReactNode } from "react";

/**
 * Reusable, lightweight guidance callout used to orient users on a page:
 * "what is this, and what do I do with it?". Keeps the visual language of the
 * live CaptureGuide (brand-tinted card, icon chip, eyebrow) without the
 * phase-specific behaviour.
 */
export function PageGuide({
  icon,
  eyebrow,
  title,
  body,
  steps,
  action,
}: {
  icon: ReactNode;
  eyebrow: string;
  title: string;
  body: string;
  steps?: { label: string; body: string }[];
  action?: { label: string; href: string };
}) {
  return (
    <section className="rounded-2xl border border-brand/25 bg-brand/[0.05] p-5 shadow-sm sm:p-6">
      <div className="flex items-start gap-4">
        <div className="hidden h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand/12 text-brand sm:inline-flex">
          {icon}
        </div>
        <div className="min-w-0 flex-1">
          <span className="mb-2 inline-flex items-center gap-1.5 rounded-full bg-brand/15 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-[0.16em] text-brand">
            {eyebrow}
          </span>
          <h2 className="text-lg font-bold tracking-tight text-foreground text-balance sm:text-xl">
            {title}
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-foreground-muted">{body}</p>

          {steps && steps.length > 0 ? (
            <ol className="mt-5 grid gap-3 sm:grid-cols-3">
              {steps.map((step, i) => (
                <li
                  key={step.label}
                  className="rounded-xl border border-border bg-surface/70 p-3.5"
                >
                  <div className="mb-1.5 flex items-center gap-2">
                    <span className="inline-flex h-6 w-6 items-center justify-center rounded-lg bg-brand/10 text-[11px] font-bold text-brand">
                      {i + 1}
                    </span>
                    <p className="text-sm font-semibold text-foreground">{step.label}</p>
                  </div>
                  <p className="text-xs leading-5 text-foreground-muted">{step.body}</p>
                </li>
              ))}
            </ol>
          ) : null}

          {action ? (
            <Link
              href={action.href}
              className="group mt-5 inline-flex items-center gap-1.5 text-sm font-semibold text-brand transition hover:underline"
            >
              {action.label}
              <ArrowRight
                size={15}
                strokeWidth={2.5}
                className="transition group-hover:translate-x-0.5"
              />
            </Link>
          ) : null}
        </div>
      </div>
    </section>
  );
}
