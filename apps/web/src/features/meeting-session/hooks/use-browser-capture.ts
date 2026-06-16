"use client";

import type { MeetingDetail, RegisterCaptureChunkRequest } from "@visualsprint/contracts";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  buildCaptureResources,
  buildClientChunkId,
  hasAudioCoverageWarning,
  resolveRecorderMimeType,
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

const UPLOAD_RETRY_ATTEMPTS = 2;

async function uploadBlobToSignedUrl(
  signedUrl: string,
  blob: Blob,
  requiredHeaders: Record<string, string>,
): Promise<void> {
  let lastError: unknown = null;
  for (let attempt = 0; attempt < UPLOAD_RETRY_ATTEMPTS; attempt += 1) {
    try {
      const response = await fetch(signedUrl, {
        method: "PUT",
        body: blob,
        headers: {
          ...requiredHeaders,
        },
      });
      if (response.ok) {
        return;
      }
      const detail = await response.text().catch(() => "unknown error");
      lastError = new Error(`Upload failed (${response.status}): ${detail}`);
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError ?? new Error("Chunk upload failed after retries");
}

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

  useEffect(() => {
    meetingRef.current = meeting;
  }, [meeting]);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const cleanupCaptureRef = useRef<(() => void) | null>(null);
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

      if (
        hasAudioCoverageWarning(
          resources.displaySurface,
          resources.hasDisplayAudio,
          resources.hasMicrophoneAudio,
        )
      ) {
        onError(
          "You are sharing only a window and no audio source was detected. Transcription may be empty unless you also share system audio or use a microphone.",
        );
      }

      const response = await startCaptureSession(currentMeeting.id, {
        recorderMimeType: preferredMimeType || null,
        hasDisplayVideo: resources.hasDisplayVideo,
        hasDisplayAudio: resources.hasDisplayAudio,
        hasMicrophoneAudio: resources.hasMicrophoneAudio,
        displaySurface: resources.displaySurface,
      });

      const recorder =
        preferredMimeType.length > 0
          ? new MediaRecorder(resources.stream, { mimeType: preferredMimeType })
          : new MediaRecorder(resources.stream);

      recorderRef.current = recorder;
      cleanupCaptureRef.current = resources.cleanup;
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
        const payload: RegisterCaptureChunkRequest = {
          clientChunkId: buildClientChunkId(response.captureSession.id, sequence),
          sequence,
          durationMs: Math.max(now - chunkStartedAtRef.current, 250),
          byteSize: event.data.size,
          mimeType: event.data.type || preferredMimeType || "video/webm",
        };
        chunkSequenceRef.current = sequence;
        chunkStartedAtRef.current = now;

        const chunkBlob = event.data;

        chunkRequestQueueRef.current = chunkRequestQueueRef.current
          .then(async () => {
            const chunkResponse = await registerCaptureChunk(activeMeeting.id, payload);
            onMeetingUpdated(chunkResponse.meeting);

            const uploadTarget = chunkResponse.chunk.uploadTarget;
            if (uploadTarget.signedUrl) {
              await uploadBlobToSignedUrl(
                uploadTarget.signedUrl,
                chunkBlob,
                uploadTarget.requiredHeaders,
              );
            }

            const uploadResponse = await completeCaptureChunkUpload(activeMeeting.id, {
              clientChunkId: payload.clientChunkId,
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
