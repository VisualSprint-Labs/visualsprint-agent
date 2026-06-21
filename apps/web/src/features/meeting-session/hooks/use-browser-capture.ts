"use client";

import type { MeetingDetail, RegisterCaptureChunkRequest } from "@visualsprint/contracts";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  blobToBase64,
  buildCaptureResources,
  buildClientChunkId,
  createKeyframeGrabber,
  resolveRecorderMimeType,
  type KeyframeGrabber,
} from "../../../lib/capture";
import { getErrorMessage } from "../../../lib/format";
import {
  completeCaptureChunkUpload,
  completeCaptureSession,
  registerCaptureChunk,
  runCaptureChunkReasoning,
  startCaptureSession,
} from "../../../lib/api";
import type { CapturePhase } from "../types";
import type { CaptureSupport } from "../../../hooks/use-capture-support";

export function useBrowserCapture({
  meeting,
  captureSupport,
  onMeetingUpdated,
  onError,
}: {
  meeting: MeetingDetail | null;
  captureSupport: CaptureSupport | null;
  onMeetingUpdated: (meeting: MeetingDetail) => void;
  onError: (message: string) => void;
}) {
  const [capturePhase, setCapturePhase] = useState<CapturePhase>("idle");
  const meetingRef = useRef(meeting);
  meetingRef.current = meeting;

  const recorderRef = useRef<MediaRecorder | null>(null);
  const cleanupCaptureRef = useRef<(() => void) | null>(null);
  const keyframeGrabberRef = useRef<KeyframeGrabber | null>(null);
  const chunkSequenceRef = useRef(0);
  const chunkStartedAtRef = useRef(0);
  const chunkRequestQueueRef = useRef<Promise<void>>(Promise.resolve());
  const stopPromiseRef = useRef<Promise<void> | null>(null);
  const stopResolverRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    return () => {
      cleanupCaptureRef.current?.();
    };
  }, []);

  const finalizeCaptureSession = useCallback(
    async (meetingId: string) => {
      try {
        await chunkRequestQueueRef.current;
        const response = await completeCaptureSession(meetingId);
        onMeetingUpdated(response.meeting);
      } catch (captureError) {
        onError(getErrorMessage(captureError));
      } finally {
        cleanupCaptureRef.current?.();
        cleanupCaptureRef.current = null;
        recorderRef.current = null;
        setCapturePhase("idle");
        stopResolverRef.current?.();
        stopResolverRef.current = null;
        stopPromiseRef.current = null;
      }
    },
    [onError, onMeetingUpdated],
  );

  const stopBrowserCapture = useCallback(async () => {
    const currentMeeting = meetingRef.current;
    if (!currentMeeting || capturePhase !== "recording" || !recorderRef.current) {
      return;
    }

    setCapturePhase("stopping");

    if (!stopPromiseRef.current) {
      stopPromiseRef.current = new Promise<void>((resolve) => {
        stopResolverRef.current = resolve;
      });
    }

    recorderRef.current.stop();
    await stopPromiseRef.current;
  }, [capturePhase]);

  const beginBrowserCapture = useCallback(async () => {
    const currentMeeting = meetingRef.current;
    if (!currentMeeting) {
      return;
    }
    if (currentMeeting.sourceConnector !== "browser_live_capture") {
      onError("Browser capture is only available for meetings using the browser_live_capture connector.");
      return;
    }
    if (currentMeeting.status !== "live") {
      onError("Start the meeting session before beginning browser capture.");
      return;
    }
    if (!captureSupport?.displayCapture || !captureSupport.mediaRecorder) {
      onError("This browser environment does not support live browser capture.");
      return;
    }

    setCapturePhase("requesting");

    let resources: Awaited<ReturnType<typeof buildCaptureResources>> | null = null;

    try {
      resources = await buildCaptureResources();
      const preferredMimeType = resolveRecorderMimeType();
      const response = await startCaptureSession(currentMeeting.id, {
        recorderMimeType: preferredMimeType || null,
        hasDisplayVideo: resources.hasDisplayVideo,
        hasDisplayAudio: resources.hasDisplayAudio,
        hasMicrophoneAudio: resources.hasMicrophoneAudio,
      });

      const recorder =
        preferredMimeType.length > 0
          ? new MediaRecorder(resources.stream, { mimeType: preferredMimeType })
          : new MediaRecorder(resources.stream);

      recorderRef.current = recorder;
      keyframeGrabberRef.current = createKeyframeGrabber(resources.stream);
      cleanupCaptureRef.current = () => {
        keyframeGrabberRef.current?.dispose();
        keyframeGrabberRef.current = null;
        resources?.cleanup();
      };
      chunkSequenceRef.current = 0;
      chunkStartedAtRef.current = Date.now();
      stopPromiseRef.current = null;
      stopResolverRef.current = null;

      recorder.ondataavailable = (event) => {
        const activeMeeting = meetingRef.current;
        if (!activeMeeting || event.data.size === 0) {
          return;
        }

        const now = Date.now();
        const sequence = chunkSequenceRef.current + 1;
        const mimeType = event.data.type || preferredMimeType || "video/webm";
        const payload: RegisterCaptureChunkRequest = {
          clientChunkId: buildClientChunkId(response.captureSession.id, sequence),
          sequence,
          durationMs: Math.max(now - chunkStartedAtRef.current, 250),
          byteSize: event.data.size,
          mimeType,
        };
        chunkSequenceRef.current = sequence;
        chunkStartedAtRef.current = now;

        // Snapshot the screen for this chunk now, before the next frame paints,
        // so the backend's multimodal vision sees what was on screen.
        const framePromise = keyframeGrabberRef.current?.grab() ?? Promise.resolve(null);

        chunkRequestQueueRef.current = chunkRequestQueueRef.current
          .then(async () => {
            const chunkResponse = await registerCaptureChunk(activeMeeting.id, payload);
            onMeetingUpdated(chunkResponse.meeting);

            const frame = await framePromise;
            const mediaBase64 =
              frame && frame.size <= 12_000_000 ? await blobToBase64(frame) : null;

            const uploadResponse = await completeCaptureChunkUpload(activeMeeting.id, {
              clientChunkId: payload.clientChunkId,
              mediaBase64,
              mediaMimeType: mediaBase64 ? "image/jpeg" : null,
            });
            onMeetingUpdated(uploadResponse.meeting);

            const reasoningResponse = await runCaptureChunkReasoning(
              activeMeeting.id,
              payload.clientChunkId,
            );
            onMeetingUpdated(reasoningResponse.meeting);
          })
          .catch((chunkError) => {
            onError(getErrorMessage(chunkError));
          });
      };

      recorder.onstop = () => {
        void finalizeCaptureSession(currentMeeting.id);
      };

      recorder.start(4000);
      onMeetingUpdated(response.meeting);
      setCapturePhase("recording");
    } catch (captureError) {
      resources?.cleanup();
      cleanupCaptureRef.current = null;
      recorderRef.current = null;
      setCapturePhase("idle");
      onError(getErrorMessage(captureError));
    }
  }, [captureSupport, finalizeCaptureSession, onError, onMeetingUpdated]);

  const canStartCapture =
    meeting?.status === "live" &&
    meeting.sourceConnector === "browser_live_capture" &&
    capturePhase === "idle";

  return {
    capturePhase,
    canStartCapture,
    beginBrowserCapture,
    stopBrowserCapture,
  };
}
