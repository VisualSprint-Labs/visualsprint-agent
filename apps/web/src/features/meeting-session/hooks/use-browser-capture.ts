"use client";

import type { MeetingDetail, RegisterCaptureChunkRequest } from "@visualsprint/contracts";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  blobToBase64,
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

// Length of each capture window. Each window is recorded as a *standalone*,
// independently-decodable webm (audio + video) by starting a fresh MediaRecorder
// per window — a single recorder with a timeslice only makes the first blob
// decodable, which is why audio (and therefore transcript) never worked before.
const CHUNK_MS = 5000;
// Skip the multimodal upload for unusually large windows (very busy screens) so
// a single chunk can't blow up the request; the chunk is still registered.
const MAX_MEDIA_BYTES = 14_000_000;

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

  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const cleanupCaptureRef = useRef<(() => void) | null>(null);
  const recordingActiveRef = useRef(false);
  const chunkTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const mimeTypeRef = useRef<string>("video/webm");
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
        streamRef.current = null;
        setCapturePhase("idle");
        stopResolverRef.current?.();
        stopResolverRef.current = null;
        stopPromiseRef.current = null;
      }
    },
    [onError, onMeetingUpdated],
  );

  // Queue the backend work for one finished capture window. Errors here are
  // benign races (e.g. a final window landing just after the session is marked
  // complete) — surface real failures but swallow the expected "not recording".
  const processChunk = useCallback(
    (meetingId: string, sessionId: string, blob: Blob) => {
      const now = Date.now();
      const sequence = chunkSequenceRef.current + 1;
      chunkSequenceRef.current = sequence;
      const startedAt = chunkStartedAtRef.current || now;
      chunkStartedAtRef.current = now;

      const payload: RegisterCaptureChunkRequest = {
        clientChunkId: buildClientChunkId(sessionId, sequence),
        sequence,
        durationMs: Math.min(Math.max(now - startedAt, 250), 120_000),
        byteSize: blob.size,
        mimeType: blob.type || mimeTypeRef.current || "video/webm",
      };

      chunkRequestQueueRef.current = chunkRequestQueueRef.current
        .then(async () => {
          const chunkResponse = await registerCaptureChunk(meetingId, payload);
          onMeetingUpdated(chunkResponse.meeting);

          const mediaBase64 = blob.size <= MAX_MEDIA_BYTES ? await blobToBase64(blob) : null;
          const uploadResponse = await completeCaptureChunkUpload(meetingId, {
            clientChunkId: payload.clientChunkId,
            mediaBase64,
            mediaMimeType: mediaBase64 ? payload.mimeType : null,
          });
          onMeetingUpdated(uploadResponse.meeting);

          const reasoningResponse = await runCaptureChunkReasoning(
            meetingId,
            payload.clientChunkId,
          );
          onMeetingUpdated(reasoningResponse.meeting);
        })
        .catch((chunkError) => {
          const message = getErrorMessage(chunkError);
          // Expected when a trailing window finishes right as capture stops.
          if (message.includes("while the session is recording")) {
            return;
          }
          onError(message);
        });
    },
    [onError, onMeetingUpdated],
  );

  // Record exactly one standalone window, then either record the next window or
  // finalize the session if a stop was requested.
  const recordWindow = useCallback(
    (meetingId: string, sessionId: string) => {
      const stream = streamRef.current;
      if (!stream || !recordingActiveRef.current) {
        return;
      }

      const recorder =
        mimeTypeRef.current.length > 0
          ? new MediaRecorder(stream, { mimeType: mimeTypeRef.current })
          : new MediaRecorder(stream);
      recorderRef.current = recorder;
      const parts: Blob[] = [];

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          parts.push(event.data);
        }
      };

      recorder.onstop = () => {
        if (chunkTimerRef.current) {
          clearTimeout(chunkTimerRef.current);
          chunkTimerRef.current = null;
        }
        if (parts.length > 0) {
          const blob = new Blob(parts, { type: mimeTypeRef.current || "video/webm" });
          if (blob.size > 0 && meetingRef.current) {
            processChunk(meetingId, sessionId, blob);
          }
        }
        if (recordingActiveRef.current) {
          recordWindow(meetingId, sessionId);
        } else {
          void finalizeCaptureSession(meetingId);
        }
      };

      chunkStartedAtRef.current = Date.now();
      recorder.start();
      chunkTimerRef.current = setTimeout(() => {
        if (recorderRef.current && recorderRef.current.state === "recording") {
          recorderRef.current.stop();
        }
      }, CHUNK_MS);
    },
    [finalizeCaptureSession, processChunk],
  );

  const stopBrowserCapture = useCallback(async () => {
    if (!recordingActiveRef.current || capturePhase !== "recording") {
      return;
    }
    setCapturePhase("stopping");
    recordingActiveRef.current = false;

    if (!stopPromiseRef.current) {
      stopPromiseRef.current = new Promise<void>((resolve) => {
        stopResolverRef.current = resolve;
      });
    }

    if (chunkTimerRef.current) {
      clearTimeout(chunkTimerRef.current);
      chunkTimerRef.current = null;
    }
    // Stopping the active recorder flushes the current window as a complete
    // webm; its onstop handler will run finalizeCaptureSession (recording is off).
    if (recorderRef.current && recorderRef.current.state === "recording") {
      recorderRef.current.stop();
    } else {
      void finalizeCaptureSession(meetingRef.current?.id ?? "");
    }

    await stopPromiseRef.current;
  }, [capturePhase, finalizeCaptureSession]);

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

      streamRef.current = resources.stream;
      mimeTypeRef.current = preferredMimeType || "video/webm";
      sessionIdRef.current = response.captureSession.id;
      chunkSequenceRef.current = 0;
      chunkStartedAtRef.current = Date.now();
      stopPromiseRef.current = null;
      stopResolverRef.current = null;
      const capturedResources = resources;
      cleanupCaptureRef.current = () => {
        capturedResources?.cleanup();
      };

      // If the user stops the screen-share from the browser's own UI, end cleanly.
      resources.stream.getVideoTracks().forEach((track) => {
        track.addEventListener("ended", () => {
          void stopBrowserCapture();
        });
      });

      recordingActiveRef.current = true;
      onMeetingUpdated(response.meeting);
      setCapturePhase("recording");
      recordWindow(currentMeeting.id, response.captureSession.id);
    } catch (captureError) {
      recordingActiveRef.current = false;
      resources?.cleanup();
      cleanupCaptureRef.current = null;
      recorderRef.current = null;
      streamRef.current = null;
      setCapturePhase("idle");
      onError(getErrorMessage(captureError));
    }
  }, [captureSupport, onError, onMeetingUpdated, recordWindow, stopBrowserCapture]);

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
