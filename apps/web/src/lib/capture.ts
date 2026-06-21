export type CaptureResources = {
  stream: MediaStream;
  cleanup: () => void;
  hasDisplayVideo: boolean;
  hasDisplayAudio: boolean;
  hasMicrophoneAudio: boolean;
};

export function buildClientChunkId(captureSessionId: string, sequence: number) {
  return `${captureSessionId}_chunk_${String(sequence).padStart(4, "0")}`;
}

/** Encode a captured media blob as a base64 string (no data: prefix). */
export async function blobToBase64(blob: Blob): Promise<string> {
  const buffer = await blob.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  let binary = "";
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}

export type KeyframeGrabber = {
  /** Grab the current screen frame as a downscaled JPEG, or null if unavailable. */
  grab: () => Promise<Blob | null>;
  dispose: () => void;
};

/**
 * Build a keyframe grabber bound to the display video track.
 *
 * MediaRecorder timeslice blobs after the first are non-standalone webm
 * fragments, so we instead snapshot an independently-decodable still frame per
 * chunk for the backend's multimodal vision pass.
 */
export function createKeyframeGrabber(
  stream: MediaStream,
  maxWidth = 1280,
): KeyframeGrabber | null {
  if (typeof document === "undefined") {
    return null;
  }
  const videoTrack = stream.getVideoTracks()[0];
  if (!videoTrack) {
    return null;
  }

  const video = document.createElement("video");
  video.muted = true;
  video.playsInline = true;
  video.srcObject = new MediaStream([videoTrack]);
  const ready = video.play().catch(() => undefined);

  const canvas = document.createElement("canvas");

  return {
    grab: async () => {
      await ready;
      const width = video.videoWidth;
      const height = video.videoHeight;
      if (!width || !height) {
        return null;
      }
      const scale = Math.min(1, maxWidth / width);
      canvas.width = Math.round(width * scale);
      canvas.height = Math.round(height * scale);
      const context = canvas.getContext("2d");
      if (!context) {
        return null;
      }
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      return await new Promise<Blob | null>((resolve) =>
        canvas.toBlob((blob) => resolve(blob), "image/jpeg", 0.7),
      );
    },
    dispose: () => {
      video.srcObject = null;
      video.remove();
      canvas.remove();
    },
  };
}

export function resolveRecorderMimeType() {
  const candidates = [
    "video/webm;codecs=vp9,opus",
    "video/webm;codecs=vp8,opus",
    "video/webm;codecs=h264,opus",
    "video/webm",
  ];

  if (typeof MediaRecorder === "undefined") {
    return "";
  }

  return candidates.find((candidate) => MediaRecorder.isTypeSupported(candidate)) ?? "";
}

export async function buildCaptureResources(): Promise<CaptureResources> {
  const displayStream = await navigator.mediaDevices.getDisplayMedia({
    video: true,
    audio: true,
  });

  let microphoneStream: MediaStream | null = null;
  try {
    microphoneStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch {
    microphoneStream = null;
  }

  const composedStream = new MediaStream();
  const cleanupCallbacks: Array<() => void> = [];

  const displayVideoTracks = displayStream.getVideoTracks();
  const displayAudioTracks = displayStream.getAudioTracks();
  const microphoneAudioTracks = microphoneStream?.getAudioTracks() ?? [];

  displayVideoTracks.forEach((track) => composedStream.addTrack(track));

  if (displayAudioTracks.length + microphoneAudioTracks.length > 1) {
    const audioContext = new AudioContext();
    const destination = audioContext.createMediaStreamDestination();
    const audioStreams: MediaStream[] = [];

    if (displayAudioTracks.length > 0) {
      audioStreams.push(new MediaStream(displayAudioTracks));
    }
    if (microphoneAudioTracks.length > 0) {
      audioStreams.push(new MediaStream(microphoneAudioTracks));
    }

    audioStreams.forEach((stream) => {
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(destination);
    });

    destination.stream.getAudioTracks().forEach((track) => composedStream.addTrack(track));

    cleanupCallbacks.push(() => {
      void audioContext.close();
    });
  } else {
    [...displayAudioTracks, ...microphoneAudioTracks].forEach((track) =>
      composedStream.addTrack(track),
    );
  }

  cleanupCallbacks.push(() => {
    displayStream.getTracks().forEach((track) => track.stop());
    microphoneStream?.getTracks().forEach((track) => track.stop());
    composedStream.getTracks().forEach((track) => {
      if (track.readyState === "live") {
        track.stop();
      }
    });
  });

  return {
    stream: composedStream,
    cleanup: () => {
      cleanupCallbacks.forEach((callback) => callback());
    },
    hasDisplayVideo: displayVideoTracks.length > 0,
    hasDisplayAudio: displayAudioTracks.length > 0,
    hasMicrophoneAudio: microphoneAudioTracks.length > 0,
  };
}
