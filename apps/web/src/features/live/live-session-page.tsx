"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";

import { MeetingTopBar } from "../../components/layout/meeting-top-bar";
import { SseLiveRegion } from "../../components/shared/sse-live-region";
import { ErrorBanner } from "../../components/shared/error-banner";
import { PageSkeleton } from "../../components/ui/skeleton";
import { Tabs } from "../../components/ui/tabs";
import { useMeetingSession } from "../meeting-session/context/meeting-session-provider";
import { CaptureGuide } from "./components/capture-guide";
import { CapturePanel } from "./components/capture-panel";
import { LiveMetricsRow } from "./components/live-metrics-row";
import { MemoryPanel } from "./components/memory-panel";
import { ReasoningPanels } from "./components/reasoning-panels";
import { RecordsPanels } from "./components/records-panels";
import { Radio, BrainCircuit, Activity } from "lucide-react";

export function LiveSessionPage() {
  const router = useRouter();
  const [mobileTab, setMobileTab] = useState("session");
  const {
    meeting,
    streamStatus,
    capturePhase,
    isBusy,
    error,
    endMeetingSession,
  } = useMeetingSession();

  useEffect(() => {
    if (!meeting) {
      return;
    }
    if (meeting.status === "draft") {
      router.replace(`/meetings/new?meetingId=${meeting.id}`);
      return;
    }
    if (meeting.status === "ended") {
      router.replace(`/meetings/${meeting.id}/report`);
    }
  }, [meeting, router]);

  if (!meeting) {
    return <PageSkeleton />;
  }

  if (meeting.status === "draft" || meeting.status === "ended") {
    return <PageSkeleton />;
  }

  const sessionPanels = (
    <div className="space-y-8">
      <CaptureGuide />
      <LiveMetricsRow meeting={meeting} />
      <CapturePanel />
    </div>
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] as const }}
      className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-5 sm:gap-8 sm:px-8 sm:py-8 lg:px-12"
    >
      <SseLiveRegion meetingTitle={meeting.title} streamStatus={streamStatus} />

      <MeetingTopBar
        capturePhase={capturePhase}
        isBusy={isBusy}
        meeting={meeting}
        onEndMeeting={() => {
          void endMeetingSession().then((didEnd) => {
            if (didEnd) {
              router.push(`/meetings/${meeting.id}/report`);
            }
          });
        }}
        streamStatus={streamStatus}
      />

      <div className="lg:hidden">
        <Tabs
          activeId={mobileTab}
          items={[
            { id: "session", label: "Session", icon: <Radio size={14} strokeWidth={2} />, content: sessionPanels },
            { id: "memory", label: "Memory", icon: <BrainCircuit size={14} strokeWidth={2} />, content: <MemoryPanel /> },
            { id: "signals", label: "Signals", icon: <Activity size={14} strokeWidth={2} />, content: <RecordsPanels /> },
          ]}
          onChange={setMobileTab}
        />
      </div>

      <div className="hidden flex-col gap-8 lg:flex">
        {sessionPanels}
        <ReasoningPanels />
      </div>

      {error ? <ErrorBanner message={error} /> : null}
    </motion.div>
  );
}
