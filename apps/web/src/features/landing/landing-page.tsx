"use client";

import Link from "next/link";
import { motion, useScroll, useTransform } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import {
  Play,
  ArrowRight,
  FileCheck,
  Radio,
  BrainCircuit,
  FileText,
  GitCommitHorizontal,
  CheckSquare,
  Monitor,
  Mic,
  Search,
  Zap,
  UserX,
  ClipboardList,
  RotateCcw,
  MessageSquare,
  Shield,
  Sparkles,
} from "lucide-react";

import { ThemeWrapper } from "../../components/layout/theme-wrapper";
import { Button } from "../../components/ui/button";
import { HeroMockup } from "../../components/ui/hero-mockup";

/* ──────────────────────────  Data  ────────────────────────── */

const highlights = [
  {
    title: "Multi-agent intelligence",
    body: "Dedicated agents reason over live chunks, compose final reports, and recommend workflow actions — each with a focused role in the pipeline.",
    icon: Sparkles,
  },
  {
    title: "Evidence-backed reports",
    body: "Every decision, commitment, and blocker links back to transcript and screen moments from the meeting.",
    icon: FileCheck,
  },
  {
    title: "Approved workflow actions",
    body: "Jira issue recommendations and Slack update drafts your team reviews before anything is sent.",
    icon: CheckSquare,
  },
];

const integrationItems = [
  { label: "Jira action recommendations", icon: CheckSquare },
  { label: "Slack update approvals", icon: MessageSquare },
  { label: "Evidence-backed reports", icon: FileCheck },
  { label: "Browser meeting capture", icon: Monitor },
  { label: "Multi-agent system", icon: Sparkles },
  { label: "Approval before execution", icon: Shield },
];

const pipelineSteps = [
  {
    icon: Monitor,
    label: "Capture",
    body: "Browser audio + screen context streamed in real time.",
  },
  {
    icon: Sparkles,
    label: "Agents",
    body: "Reasoning, summary, and action agents work together over each chunk and at meeting close.",
  },
  {
    icon: Search,
    label: "Memory",
    body: "Cross-meeting retrieval surfaces recurring blockers and related past decisions.",
  },
  {
    icon: FileText,
    label: "Report",
    body: "Summary agent produces an evidence-backed report with decisions, owners, and proof.",
  },
];

const problemSolutions = [
  {
    icon: UserX,
    problemTitle: "Missed meeting means missed context",
    problemBody:
      "When a team member misses an online meeting, they usually need to watch the full recording or ask others what happened.",
    solutionTitle: "Get the full context without replaying everything",
    solutionBody:
      "VisualSprint turns the meeting into a structured record with discussions, screen context, decisions, owners, and next actions.",
  },
  {
    icon: FileText,
    problemTitle: "Transcripts don't show the full story",
    problemBody:
      "A transcript only shows what people said. It does not explain the slide, demo, screen share, diagram, or product flow being discussed.",
    solutionTitle: "Capture what was said and shown",
    solutionBody:
      "VisualSprint connects conversations with screen activity so the context behind each decision is easier to understand.",
  },
  {
    icon: ClipboardList,
    problemTitle: "Meeting notes are manual and incomplete",
    problemBody:
      "Someone has to write down decisions, plans, blockers, and who will do what after the meeting.",
    solutionTitle: "Generate structured meeting reports",
    solutionBody:
      "VisualSprint creates evidence-backed reports with decisions, commitments, blockers, open questions, and ownership.",
  },
  {
    icon: GitCommitHorizontal,
    problemTitle: "Follow-up work happens after the meeting",
    problemBody:
      "Teams still need to create Jira tasks, send Slack updates, and remind owners manually.",
    solutionTitle: "Recommend workflow-ready actions",
    solutionBody:
      "VisualSprint suggests Jira issues, Slack summaries, blocker alerts, and follow-up reminders based on the meeting discussion.",
  },
  {
    icon: RotateCcw,
    problemTitle: "Decisions disappear over time",
    problemBody:
      "Teams repeat the same discussions because past decisions and blockers are difficult to find later.",
    solutionTitle: "Build searchable team knowledge",
    solutionBody:
      "Every meeting becomes structured knowledge your team can search, review, and use in future planning.",
  },
];

const footerLinks = {
  Workflow: ["Meeting capture", "Evidence reports", "Decision records", "Action recommendations"],
  Integrations: ["Jira", "Slack", "Browser capture", "Online meetings"],
  Legal: ["Privacy", "Terms", "Security", "Cookies"],
};

/* ──────────────────────────  Animation presets  ────────────────────────── */

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.08 } },
};

const item = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] as const } },
};

/* ──────────────────────────  Sub-components  ────────────────────────── */

function particleSeed(index: number, salt: number) {
  const x = Math.sin(index * 12.9898 + salt * 78.233) * 43758.5453;
  return Math.round((x - Math.floor(x)) * 10000) / 10000;
}

const heroParticles = Array.from({ length: 24 }, (_, i) => ({
  size: Math.round((particleSeed(i, 1) * 3 + 1) * 100) / 100,
  left: Math.round(particleSeed(i, 2) * 10000) / 100,
  delay: Math.round(particleSeed(i, 3) * 100) / 100,
  duration: Math.round((particleSeed(i, 4) * 15 + 15) * 100) / 100,
  opacity: Math.round((particleSeed(i, 5) * 0.5 + 0.2) * 10000) / 10000,
}));

function ParticleField() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return null;
  }

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {heroParticles.map((particle, i) => (
        <div
          key={i}
          className="particle"
          style={{
            width: `${particle.size}px`,
            height: `${particle.size}px`,
            left: `${particle.left}%`,
            bottom: `-${particle.size}px`,
            animationDelay: `${particle.delay}s`,
            animationDuration: `${particle.duration}s`,
            opacity: particle.opacity,
          }}
        />
      ))}
    </div>
  );
}

/* ──────────────────────────  Sections  ────────────────────────── */

function HeroSection() {
  return (
    <section className="relative overflow-hidden pt-12 pb-20 sm:pt-16 sm:pb-28">
      {/* Background effects */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(45,212,168,0.10),_transparent_50%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_right,_rgba(56,189,248,0.08),_transparent_50%)]" />
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
          }}
        />
      </div>
      <ParticleField />

      <div className="relative mx-auto flex max-w-7xl flex-col gap-12 px-4 sm:px-8 lg:px-10">
        <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">
          {/* Text */}
          <motion.div
            variants={container}
            initial="hidden"
            animate="show"
            className="max-w-2xl space-y-6"
          >
            <motion.div variants={item}>
              <span className="inline-flex items-center gap-2 rounded-full bg-brand/10 px-3 py-1.5 text-xs font-medium uppercase tracking-[0.18em] text-brand shadow-glow animate-glow-pulse">
                <span className="h-1.5 w-1.5 rounded-full bg-brand live-pulse shadow-[0_0_8px_rgba(45,212,168,0.6)]" />
                Multi-agent meeting intelligence for online teams
              </span>
            </motion.div>

            <motion.h1
              variants={item}
              className="text-balance text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl xl:text-7xl"
              style={{ lineHeight: 1.08 }}
            >
              Turn meetings into{" "}
              <span className="bg-gradient-to-r from-brand via-[#5eead4] to-[#38bdf8] bg-clip-text text-transparent">
                structured knowledge
              </span>{" "}
              for your workflow
            </motion.h1>

            <motion.div variants={item} className="max-w-xl space-y-4 text-lg leading-8 sm:text-xl sm:leading-9">
              <p className="font-medium text-foreground">
                When your team misses an online meeting, they shouldn&apos;t miss the context.
              </p>
              <div className="text-[#7dd3fc] [&_p]:m-0 [&_p+p]:mt-0">
                <p className="font-medium">Skip recordings and transcript-only notes.</p>
                <p>Turn meeting context into reports, knowledge, and workflow-ready actions.</p>
              </div>
            </motion.div>

            <motion.div variants={item} className="flex flex-wrap gap-3 pt-2">
              <Link href="/meetings/new">
                <Button size="lg" leftIcon={<Play size={18} strokeWidth={2.5} />} className="shadow-lg shadow-brand/20 hover:shadow-xl hover:shadow-brand/30 transition-all hover:-translate-y-0.5">
                  Start a meeting
                </Button>
              </Link>
              <Link href="/meetings">
                <Button variant="secondary" size="lg" rightIcon={<ArrowRight size={18} strokeWidth={2} />} className="hover:-translate-y-0.5 transition-all">
                  View demo
                </Button>
              </Link>
            </motion.div>
          </motion.div>

          {/* Product screenshot */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] as const, delay: 0.3 }}
            className="relative"
          >
            <HeroMockup />
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] as const, delay: 0.5 }}
          className="mx-auto max-w-3xl rounded-2xl border border-brand/25 bg-brand/[0.06] px-6 py-4 text-center shadow-lg shadow-brand/5 sm:px-8 sm:py-5"
        >
          <p className="text-base font-medium leading-7 text-foreground sm:text-lg sm:leading-8">
            Transform meeting conversations into{" "}
            <span className="bg-gradient-to-r from-brand via-[#5eead4] to-[#38bdf8] bg-clip-text font-semibold text-transparent">
              decisions, plans, and Jira/Slack actions
            </span>
            .
          </p>
        </motion.div>
      </div>
    </section>
  );
}

function IntegrationStrip() {
  return (
    <section className="relative border-y border-border bg-[var(--ink-bg-elevated)]/50 py-8 sm:py-10">
      <div className="mx-auto max-w-7xl px-4 sm:px-8 lg:px-10">
        <p className="mb-6 text-center text-xs font-semibold uppercase tracking-[0.2em] text-foreground-muted">
          Built for your engineering workflow
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3 sm:gap-4">
          {integrationItems.map((entry) => {
            const Icon = entry.icon;
            return (
              <span
                key={entry.label}
                className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-4 py-2 text-sm text-foreground-muted shadow-sm"
              >
                <Icon size={16} strokeWidth={2} className="shrink-0 text-brand" />
                {entry.label}
              </span>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function FeaturesSection() {
  return (
    <section className="relative py-20 sm:py-28">
      <div className="mx-auto max-w-7xl px-4 sm:px-8 lg:px-10">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] as const }}
          className="mb-14 text-center"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand">Features</p>
          <h2 className="mx-auto mt-3 max-w-2xl text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            Everything you need to remember everything
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-foreground-muted">
            Three pillars that turn chaotic meetings into structured, actionable intelligence.
          </p>
        </motion.div>

        <motion.div
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-60px" }}
          className="grid gap-6 md:grid-cols-3"
        >
          {highlights.map((f) => {
            const Icon = f.icon;
            return (
              <motion.article
                key={f.title}
                variants={item}
                className="group relative rounded-2xl border border-border bg-surface p-8 shadow-md transition-all duration-300 hover:-translate-y-1 hover:border-brand/30 hover:shadow-xl hover:shadow-brand/5"
              >
                <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-brand/30 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
                <div className="mb-6 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-brand/10 text-brand transition group-hover:bg-brand/20">
                  <Icon size={24} strokeWidth={2} />
                </div>
                <h3 className="text-xl font-semibold tracking-tight">{f.title}</h3>
                <p className="mt-3 text-sm leading-7 text-foreground-muted">{f.body}</p>
              </motion.article>
            );
          })}
        </motion.div>
      </div>
    </section>
  );
}

function HowItWorksSection() {
  return (
    <section className="relative py-20 sm:py-28">
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-brand/[0.02] to-transparent" />
      <div className="relative mx-auto max-w-7xl px-4 sm:px-8 lg:px-10">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] as const }}
          className="mb-14 text-center"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand">How it works</p>
          <h2 className="mx-auto mt-3 max-w-2xl text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            From capture to evidence-backed report
          </h2>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] as const }}
          className="mx-auto mb-12 max-w-4xl rounded-2xl border border-brand/25 bg-brand/[0.06] px-6 py-5 text-center shadow-lg shadow-brand/5 sm:px-8"
        >
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-brand">Multi-agent system</p>
          <p className="mt-3 text-base leading-7 text-foreground sm:text-lg sm:leading-8">
            A{" "}
            <span className="bg-gradient-to-r from-brand via-[#5eead4] to-[#38bdf8] bg-clip-text font-semibold text-transparent">
              reasoning agent
            </span>{" "}
            analyzes live transcript and screen context, a{" "}
            <span className="bg-gradient-to-r from-brand via-[#5eead4] to-[#38bdf8] bg-clip-text font-semibold text-transparent">
              summary agent
            </span>{" "}
            composes the final report, and an{" "}
            <span className="bg-gradient-to-r from-brand via-[#5eead4] to-[#38bdf8] bg-clip-text font-semibold text-transparent">
              action agent
            </span>{" "}
            recommends Jira and Slack updates for your team to approve.
          </p>
        </motion.div>

        <div className="relative">
          {/* Connector line desktop */}
          <div className="absolute left-0 right-0 top-10 hidden h-px lg:block">
            <div className="relative mx-auto h-full w-3/4 overflow-hidden rounded-full bg-[var(--ink-border)]">
              <motion.div
                initial={{ x: "-100%" }}
                whileInView={{ x: "100%" }}
                viewport={{ once: true }}
                transition={{ duration: 1.8, ease: [0.16, 1, 0.3, 1] as const, delay: 0.3 }}
                className="h-full w-1/2 bg-gradient-to-r from-transparent via-brand to-transparent"
              />
            </div>
          </div>

          <motion.div
            variants={container}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-60px" }}
            className="relative grid gap-6 sm:grid-cols-2 lg:grid-cols-4"
          >
            {pipelineSteps.map((step, i) => {
              const Icon = step.icon;
              return (
                <motion.div
                  key={step.label}
                  variants={item}
                  className="group relative flex flex-col items-center text-center"
                >
                  <div className="relative z-10 mb-4 inline-flex h-14 w-14 items-center justify-center rounded-xl border border-[var(--ink-border)] bg-[var(--ink-surface)] shadow-lg transition-all duration-300 group-hover:-translate-y-1 group-hover:border-brand/40 group-hover:shadow-glow">
                    <Icon size={24} strokeWidth={2} className="text-brand" />
                  </div>
                  <div className="rounded-xl border border-[var(--ink-border)] bg-[var(--ink-surface)] p-5 shadow-md transition-all duration-200 group-hover:border-border-strong group-hover:shadow-lg">
                    <div className="mb-2 flex items-center justify-center gap-2">
                      <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-brand/10 text-xs font-bold text-brand">
                        {i + 1}
                      </span>
                      <h3 className="text-sm font-semibold tracking-tight text-[var(--ink-fg)]">
                        {step.label}
                      </h3>
                    </div>
                    <p className="text-xs leading-5 text-[var(--ink-fg-muted)]">{step.body}</p>
                  </div>
                </motion.div>
              );
            })}
          </motion.div>
        </div>
      </div>
    </section>
  );
}

function LiveDemoSection() {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"],
  });
  const y = useTransform(scrollYProgress, [0, 1], [40, -40]);

  return (
    <section ref={ref} className="relative overflow-hidden py-20 sm:py-28">
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#38bdf8]/[0.03] to-transparent" />
      <div className="relative mx-auto max-w-7xl px-4 sm:px-8 lg:px-10">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] as const }}
          className="mb-14 text-center"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#38bdf8]">Live Demo</p>
          <h2 className="mx-auto mt-3 max-w-3xl text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            Transform meeting conversations into decisions, plans, and Jira/Slack actions.
          </h2>
        </motion.div>

        <motion.div style={{ y }} className="relative mx-auto max-w-5xl">
          <div className="relative overflow-hidden rounded-2xl border border-border-strong bg-[var(--ink-surface)] shadow-2xl demo-scanline">
            {/* Scanline overlay */}
            <div className="absolute inset-0 pointer-events-none z-10 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.15)_50%),linear-gradient(90deg,rgba(255,0,0,0.03),rgba(0,255,0,0.01),rgba(0,0,255,0.03))] bg-[length:100%_4px,3px_100%] opacity-20" />

            {/* Header bar */}
            <div className="flex items-center justify-between border-b border-border px-5 py-3">
              <div className="flex items-center gap-2">
                <div className="flex gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-full bg-[var(--status-error)]/70" />
                  <span className="h-2.5 w-2.5 rounded-full bg-[var(--status-draft)]/70" />
                  <span className="h-2.5 w-2.5 rounded-full bg-[var(--status-live)]/70" />
                </div>
                <span className="ml-3 text-xs text-foreground-muted">visualsprint.app/live</span>
              </div>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-[var(--status-live)]/10 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-[var(--status-live)]">
                <Radio size={10} strokeWidth={2.5} className="live-pulse" />
                Capturing
              </span>
            </div>

            <div className="grid gap-px bg-border lg:grid-cols-3">
              {/* Left: Transcript */}
              <div className="bg-[var(--ink-surface)] p-5">
                <div className="mb-4 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-foreground-muted">
                  <Mic size={14} strokeWidth={2} />
                  Transcript
                </div>
                <div className="space-y-3">
                  {[
                    { w: "85%", highlight: false },
                    { w: "60%", highlight: true },
                    { w: "90%", highlight: false },
                    { w: "45%", highlight: true },
                    { w: "75%", highlight: false },
                  ].map((line, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <div className="mt-1 h-5 w-5 shrink-0 rounded-full bg-surface-2" />
                      <div className="flex-1 space-y-1.5">
                        <div className="h-2 rounded bg-surface-2" style={{ width: line.w }} />
                        {line.highlight && (
                          <div className="h-2 rounded bg-brand/20" style={{ width: "40%" }} />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Center: Decisions */}
              <div className="bg-[var(--ink-surface)] p-5">
                <div className="mb-4 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-foreground-muted">
                  <GitCommitHorizontal size={14} strokeWidth={2} />
                  Decisions
                </div>
                <div className="space-y-3">
                  {[
                    { label: "Migrate to new auth service", color: "border-brand/30 bg-brand/5" },
                    { label: "Deprecate legacy API v1", color: "border-[#38bdf8]/30 bg-[#38bdf8]/5" },
                    { label: "Adopt pnpm monorepo", color: "border-brand/30 bg-brand/5" },
                  ].map((d, i) => (
                    <div
                      key={i}
                      className={`rounded-lg border ${d.color} p-3 transition hover:-translate-y-0.5`}
                    >
                      <div className="flex items-center gap-2">
                        <CheckSquare size={14} strokeWidth={2} className="text-brand" />
                        <span className="text-sm font-medium">{d.label}</span>
                      </div>
                      <div className="mt-2 h-1.5 w-2/3 rounded bg-surface-2" />
                    </div>
                  ))}
                </div>
              </div>

              {/* Right: Memory */}
              <div className="bg-[var(--ink-surface)] p-5">
                <div className="mb-4 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-foreground-muted">
                  <Search size={14} strokeWidth={2} />
                  Memory Matches
                </div>
                <div className="space-y-3">
                  {[
                    { title: "Similar blocker: Jan 12", type: "Recurring" },
                    { title: "Auth migration — Q4 plan", type: "Related" },
                    { title: "API v1 sunset discussion", type: "Previous" },
                  ].map((m, i) => (
                    <div
                      key={i}
                      className="rounded-lg border border-border bg-surface-2 p-3 transition hover:-translate-y-0.5 hover:border-[var(--accent-memory)]/30"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">{m.title}</span>
                        <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--accent-memory)]">
                          {m.type}
                        </span>
                      </div>
                      <div className="mt-2 h-1.5 w-1/2 rounded bg-surface-muted" />
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Bottom bar */}
            <div className="flex items-center justify-between border-t border-border px-5 py-3">
              <div className="flex items-center gap-4 text-xs text-foreground-muted">
                <span className="flex items-center gap-1.5">
                  <Monitor size={12} strokeWidth={2} />
                  12 captures
                </span>
                <span className="flex items-center gap-1.5">
                  <BrainCircuit size={12} strokeWidth={2} />
                  4 insights
                </span>
              </div>
              <div className="h-2 w-24 rounded-full bg-surface-2">
                <div className="h-full w-3/4 rounded-full bg-brand/40" />
              </div>
            </div>
          </div>

          {/* Glow */}
          <div
            className="pointer-events-none absolute -bottom-10 left-1/2 h-32 w-3/4 -translate-x-1/2 rounded-full opacity-40 blur-3xl"
            style={{ background: "radial-gradient(circle, rgba(56,189,248,0.20), transparent 70%)" }}
          />
        </motion.div>
      </div>
    </section>
  );
}

function ProblemSolutionSection() {
  return (
    <section className="relative py-20 sm:py-28">
      <div className="mx-auto max-w-7xl px-4 sm:px-8 lg:px-10">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] as const }}
          className="mb-14 text-center"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-foreground-muted">The problem</p>
          <h2 className="mx-auto mt-3 max-w-2xl text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            Why meeting context gets lost
          </h2>
        </motion.div>

        <motion.div
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-60px" }}
          className="space-y-5"
        >
          {problemSolutions.map((card) => {
            const Icon = card.icon;
            return (
              <motion.article
                key={card.problemTitle}
                variants={item}
                className="overflow-hidden rounded-2xl border border-border bg-surface shadow-md transition hover:border-border-strong hover:shadow-lg"
              >
                <div className="grid md:grid-cols-2">
                  <div className="flex items-start gap-4 border-b border-border p-6 md:border-b-0 md:border-r">
                    <div className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--status-error)]/10 text-[var(--status-error)]">
                      <Icon size={18} strokeWidth={2} />
                    </div>
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-[var(--status-error)]">
                        Problem
                      </p>
                      <h3 className="mt-1 text-base font-semibold text-foreground">{card.problemTitle}</h3>
                      <p className="mt-2 text-sm leading-6 text-foreground-muted">{card.problemBody}</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-4 bg-brand/[0.03] p-6">
                    <div className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand/10 text-brand">
                      <CheckSquare size={18} strokeWidth={2} />
                    </div>
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-brand">Solution</p>
                      <h3 className="mt-1 text-base font-semibold text-foreground">{card.solutionTitle}</h3>
                      <p className="mt-2 text-sm leading-6 text-foreground-muted">{card.solutionBody}</p>
                    </div>
                  </div>
                </div>
              </motion.article>
            );
          })}
        </motion.div>
      </div>
    </section>
  );
}

function PrivacySection() {
  return (
    <section className="relative py-16 sm:py-20">
      <div className="mx-auto max-w-4xl px-4 sm:px-8 lg:px-10">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] as const }}
          className="rounded-2xl border border-border bg-surface p-8 text-center shadow-md sm:p-10"
        >
          <div className="mx-auto mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-brand/10 text-brand">
            <Shield size={24} strokeWidth={2} />
          </div>
          <h2 className="text-balance text-2xl font-bold tracking-tight sm:text-3xl">
            No silent recording. No hidden sharing.
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-sm leading-7 text-foreground-muted sm:text-base">
            VisualSprint only captures meetings your team starts, then uses that context to create your
            private reports and approved workflow actions.
          </p>
        </motion.div>
      </div>
    </section>
  );
}

function CTABanner() {
  return (
    <section className="relative py-20 sm:py-28">
      <div className="mx-auto max-w-5xl px-4 sm:px-8 lg:px-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] as const }}
          className="relative overflow-hidden rounded-3xl border border-border bg-gradient-to-br from-[var(--ink-surface)] to-[var(--ink-surface-2)] p-10 text-center shadow-2xl sm:p-16"
        >
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(45,212,168,0.08),_transparent_50%)]" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_bottom_left,_rgba(56,189,248,0.06),_transparent_50%)]" />

          <div className="relative">
            <h2 className="text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
              Ready to turn virtual meetings into structured knowledge?
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-foreground-muted">
              Make every meeting searchable, actionable, and easy to follow up.
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <Link href="/meetings/new">
                <Button size="lg" leftIcon={<Zap size={18} strokeWidth={2.5} />} className="shadow-lg shadow-brand/20 hover:shadow-xl hover:shadow-brand/30 transition-all hover:-translate-y-0.5">
                  Start a meeting
                </Button>
              </Link>
              <Link href="/meetings">
                <Button variant="secondary" size="lg" rightIcon={<ArrowRight size={18} strokeWidth={2} />} className="hover:-translate-y-0.5 transition-all">
                  View demo
                </Button>
              </Link>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-border bg-[var(--ink-bg-elevated)]/50">
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-8 lg:px-10">
        <div className="grid gap-12 md:grid-cols-2 lg:grid-cols-5">
          {/* Brand */}
          <div className="lg:col-span-2">
            <Link href="/" className="flex items-center gap-3">
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-brand text-sm font-bold text-brand-fg">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M2 17L12 22L22 17" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M2 12L12 17L22 12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </span>
              <span className="text-lg font-semibold tracking-tight">VisualSprint</span>
            </Link>
            <p className="mt-4 max-w-sm text-sm leading-6 text-foreground-muted">
              Meeting intelligence for online engineering teams. Turn meeting context into structured
              knowledge, reports, and approved workflow actions.
            </p>
          </div>

          {/* Links */}
          {Object.entries(footerLinks).map(([category, links]) => (
            <div key={category}>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-foreground">{category}</h4>
              <ul className="mt-4 space-y-2.5">
                {links.map((link) => (
                  <li key={link}>
                    <a href="#" className="text-sm text-foreground-muted transition hover:text-foreground">
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 border-t border-border pt-8">
          <p className="text-center text-xs leading-6 text-foreground-muted sm:text-sm">
            No silent recording. No hidden sharing. Your team controls capture and approves workflow
            actions.
          </p>
          <p className="mt-4 text-center text-xs text-foreground-subtle">
            © 2026 VisualSprint. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}

/* ──────────────────────────  Page export  ────────────────────────── */

export function LandingPage() {
  return (
    <ThemeWrapper theme="ink">
      <div className="relative">
        <HeroSection />
        <IntegrationStrip />
        <FeaturesSection />
        <HowItWorksSection />
        <LiveDemoSection />
        <ProblemSolutionSection />
        <PrivacySection />
        <CTABanner />
        <Footer />
      </div>
    </ThemeWrapper>
  );
}
