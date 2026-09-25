import type { AssetWarningCode } from "./types";

/**
 * MOCK/LOCAL image quality validation — runs entirely in the browser with
 * <canvas>, no backend vision model involved yet. Real product should call
 * something like `POST /api/assets/{id}/validate` and replace this module,
 * keeping the same `{ code, message } | null` result shape so the calling
 * UI doesn't need to change.
 */

export type ImageAnalysisResult = {
  width: number;
  height: number;
  warningCode?: AssetWarningCode;
};

const SUPPORTED_TYPES = ["image/jpeg", "image/jpg", "image/png", "image/webp"];
const MIN_DIMENSION = 480;
const DARK_BRIGHTNESS_THRESHOLD = 55; // 0-255 scale
const BLUR_VARIANCE_THRESHOLD = 18; // approximate edge-energy threshold
const EXTREME_ASPECT_RATIO = 2.6; // width:height or height:width beyond this looks cropped

export function isSupportedImageType(file: File): boolean {
  return SUPPORTED_TYPES.includes(file.type);
}

/**
 * Loads the file into an offscreen canvas and runs a few cheap heuristics:
 * average brightness (too dark), a Laplacian-style edge-energy estimate
 * (blurry), raw pixel dimensions (low resolution), and aspect-ratio extremes
 * (possibly cropped). Rejects outright on corrupt/unreadable files.
 */
export async function analyzeImageFile(file: File): Promise<ImageAnalysisResult> {
  if (!isSupportedImageType(file)) {
    return { width: 0, height: 0, warningCode: "UNSUPPORTED" };
  }

  const objectUrl = URL.createObjectURL(file);
  try {
    const image = await loadImage(objectUrl);
    const { width, height } = image;

    if (!width || !height) {
      return { width: 0, height: 0, warningCode: "CORRUPT" };
    }

    const canvas = document.createElement("canvas");
    // Downscale for fast pixel analysis; quality checks don't need full res.
    const scale = Math.min(1, 256 / Math.max(width, height));
    canvas.width = Math.max(1, Math.round(width * scale));
    canvas.height = Math.max(1, Math.round(height * scale));
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    if (!ctx) return { width, height };

    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
    const { data } = ctx.getImageData(0, 0, canvas.width, canvas.height);

    const brightness = averageBrightness(data);
    const sharpness = edgeEnergy(data, canvas.width, canvas.height);
    const aspectRatio = Math.max(width / height, height / width);

    let warningCode: AssetWarningCode | undefined;
    if (Math.min(width, height) < MIN_DIMENSION) {
      warningCode = "LOW_RESOLUTION";
    } else if (aspectRatio > EXTREME_ASPECT_RATIO) {
      warningCode = "CROPPED";
    } else if (brightness < DARK_BRIGHTNESS_THRESHOLD) {
      warningCode = "TOO_DARK";
    } else if (sharpness < BLUR_VARIANCE_THRESHOLD) {
      warningCode = "BLURRY";
    }

    return { width, height, warningCode };
  } catch {
    return { width: 0, height: 0, warningCode: "CORRUPT" };
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("Image failed to load"));
    img.src = src;
  });
}

function averageBrightness(data: Uint8ClampedArray): number {
  let total = 0;
  const pixelCount = data.length / 4;
  for (let i = 0; i < data.length; i += 4) {
    // Perceptual luminance weighting.
    total += data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114;
  }
  return total / pixelCount;
}

/** Cheap grayscale gradient-magnitude estimate used as a sharpness proxy. */
function edgeEnergy(data: Uint8ClampedArray, width: number, height: number): number {
  const gray = new Float32Array(width * height);
  for (let i = 0, p = 0; i < data.length; i += 4, p += 1) {
    gray[p] = data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114;
  }

  let sumSquares = 0;
  let sum = 0;
  let count = 0;
  for (let y = 1; y < height - 1; y++) {
    for (let x = 1; x < width - 1; x++) {
      const idx = y * width + x;
      const gx = gray[idx + 1] - gray[idx - 1];
      const gy = gray[idx + width] - gray[idx - width];
      const magnitude = Math.sqrt(gx * gx + gy * gy);
      sum += magnitude;
      sumSquares += magnitude * magnitude;
      count += 1;
    }
  }
  if (count === 0) return 0;
  const mean = sum / count;
  const variance = sumSquares / count - mean * mean;
  return Math.sqrt(Math.max(variance, 0));
}

export function warningMessageKey(code: AssetWarningCode): string {
  switch (code) {
    case "BLURRY":
      return "chat.validation.blurry";
    case "LOW_RESOLUTION":
      return "chat.validation.lowResolution";
    case "TOO_DARK":
      return "chat.validation.tooDark";
    case "CROPPED":
      return "chat.validation.cropped";
    case "CORRUPT":
      return "chat.validation.corrupt";
    case "UNSUPPORTED":
      return "chat.validation.unsupported";
    default:
      return "chat.validation.valid";
  }
}

export function isHardRejection(code?: AssetWarningCode): boolean {
  return code === "CORRUPT" || code === "UNSUPPORTED";
}
