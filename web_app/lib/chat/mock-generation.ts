import type { GenerationStageKey } from "./types";

/**
 * MOCK generation runner — simulates the backend job lifecycle so the UI's
 * progress card, stage list, and result view can be built/demoed without a
 * real video pipeline. Replace with polling/SSE against
 * `GET /api/generations/{id}` later; keep the `onUpdate` callback shape.
 *
 * Internal model names are intentionally never referenced here or anywhere
 * in the UI layer — only user-facing stage labels are exposed.
 */

const STAGE_SEQUENCE: { stage: GenerationStageKey; atProgress: number; delayMs: number }[] = [
  { stage: "QUEUED", atProgress: 5, delayMs: 400 },
  { stage: "PREPARING", atProgress: 20, delayMs: 900 },
  { stage: "GENERATING", atProgress: 65, delayMs: 2200 },
  { stage: "VALIDATING", atProgress: 85, delayMs: 900 },
  { stage: "FINALIZING", atProgress: 97, delayMs: 700 },
  { stage: "COMPLETED", atProgress: 100, delayMs: 500 },
];

// A small, well-known royalty-free sample video stands in for the real
// generated asset until the video-generation backend exists.
export const MOCK_VIDEO_URL =
  "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4";

export type MockGenerationHandle = {
  cancel: () => void;
};

export function runMockGeneration(options: {
  /** Force a failure partway through, to exercise the FAILED state. */
  forceFailure?: boolean;
  onUpdate: (update: { status: GenerationStageKey; progress: number }) => void;
  onComplete: (videoUrl: string) => void;
  onError: (message: string) => void;
}): MockGenerationHandle {
  let cancelled = false;
  const timeouts: ReturnType<typeof setTimeout>[] = [];

  const failAtIndex = options.forceFailure
    ? Math.floor(STAGE_SEQUENCE.length / 2)
    : -1;

  let elapsed = 0;
  STAGE_SEQUENCE.forEach((step, index) => {
    elapsed += step.delayMs;
    const timeout = setTimeout(() => {
      if (cancelled) return;

      if (index === failAtIndex) {
        options.onError(
          "Generation failed unexpectedly while validating the render.",
        );
        return;
      }

      options.onUpdate({ status: step.stage, progress: step.atProgress });

      if (step.stage === "COMPLETED") {
        options.onComplete(MOCK_VIDEO_URL);
      }
    }, elapsed);
    timeouts.push(timeout);
  });

  return {
    cancel: () => {
      cancelled = true;
      timeouts.forEach(clearTimeout);
    },
  };
}
