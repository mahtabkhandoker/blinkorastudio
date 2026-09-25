import type { CreativeInput, Platform, SupportedStyle } from "./types";

/**
 * MOCK NLU — local heuristic parser (no backend/LLM call yet).
 *
 * Extracts whatever it confidently can from a single free-text message so
 * the assistant only asks about what's still missing, per the "smart
 * question flow" requirement. Understands Bangla, Banglish and English,
 * including mixed-language input. This is intentionally simple pattern
 * matching — swap for a real NLU/LLM extraction endpoint later behind the
 * same `parseCreativeInput()` signature.
 */

const STYLE_KEYWORDS: Record<SupportedStyle, string[]> = {
  premium: ["premium", "প্রিমিয়াম", "luxury", "lakjhari"],
  festive: ["festive", "উৎসবমুখর", "eid", "ঈদ", "puja", "পূজা", "celebration"],
  minimal: ["minimal", "মিনিমাল", "simple", "সাধারণ"],
  energetic: ["energetic", "এনার্জেটিক", "energy", "lively", "dynamic"],
  elegant: ["elegant", "এলিগেন্ট", "graceful", "classy"],
};

const CAMPAIGN_KEYWORDS: Record<string, string[]> = {
  "Eid Campaign": ["eid", "ঈদ"],
  "Offer / Discount": ["offer", "অফার", "discount", "sale", "ছাড়"],
  "Product Launch": ["launch", "new product", "নতুন প্রোডাক্ট"],
  "Product Promo": ["promo", "promotion", "প্রোমো", "advertisement", "biggapon", "বিজ্ঞাপন"],
};

const PLATFORM_KEYWORDS: Record<Platform, string[]> = {
  facebook_instagram: ["facebook", "fb", "instagram", "insta"],
  tiktok_reels: ["tiktok", "reels", "reel"],
  youtube: ["youtube", "yt"],
};

const PLATFORM_ASPECT: Record<Platform, CreativeInput["aspectRatio"]> = {
  facebook_instagram: "1:1",
  tiktok_reels: "9:16",
  youtube: "16:9",
};

const DURATION_PATTERN = /(\d{1,2})\s*(?:sec|second|seconds|sec\.|s\b|সেকেন্ড)/i;

const BUSINESS_NAME_PATTERNS: RegExp[] = [
  // "Amar Marifa dress business ache" / "আমার Marifa dress ব্যবসা আছে"
  /\bamar\s+([a-zA-Z0-9ঀ-৿]+)\s+([a-zA-Zঀ-৿]+)\s+business\b/i,
  /আমার\s+([a-zA-Z0-9ঀ-৿]+)\s+([a-zA-Zঀ-৿]+)\s+ব্যবসা/i,
  // "My Marifa dress shop"
  /\bmy\s+([a-zA-Z0-9]+)\s+([a-zA-Z]+)\s+(?:business|shop|store)\b/i,
];

const NO_VOICEOVER_PATTERN = /\bno\s+voice.?over\b|ভয়েসওভার\s+লাগবে না|voice.?over\s+chai\s*na/i;
const NO_CAPTION_PATTERN = /\bno\s+caption\b|caption\s+bad\s+dao|ক্যাপশন\s+বাদ/i;
const CTA_PATTERN = /"([^"]{3,40})"|'([^']{3,40})'/;

export function parseCreativeInput(rawText: string): Partial<CreativeInput> {
  const text = rawText.trim();
  const lower = text.toLowerCase();
  const result: Partial<CreativeInput> = {};

  // Style (may match multiple).
  const styles = (Object.keys(STYLE_KEYWORDS) as SupportedStyle[]).filter((style) =>
    STYLE_KEYWORDS[style].some((kw) => lower.includes(kw.toLowerCase()) || text.includes(kw)),
  );
  if (styles.length) result.style = styles;

  // Campaign type.
  for (const [campaign, keywords] of Object.entries(CAMPAIGN_KEYWORDS)) {
    if (keywords.some((kw) => lower.includes(kw.toLowerCase()) || text.includes(kw))) {
      result.campaignType = campaign;
      break;
    }
  }

  // Platform + implied aspect ratio.
  for (const [platform, keywords] of Object.entries(PLATFORM_KEYWORDS) as [
    Platform,
    string[],
  ][]) {
    if (keywords.some((kw) => lower.includes(kw))) {
      result.platform = platform;
      result.aspectRatio = PLATFORM_ASPECT[platform];
      break;
    }
  }

  // Duration.
  const durationMatch = text.match(DURATION_PATTERN);
  if (durationMatch) {
    const seconds = parseInt(durationMatch[1], 10);
    if (!Number.isNaN(seconds)) result.duration = seconds;
  }

  // Business / product name (best-effort).
  for (const pattern of BUSINESS_NAME_PATTERNS) {
    const match = text.match(pattern);
    if (match) {
      result.businessName = match[1];
      result.productCategory = match[2]?.toLowerCase();
      break;
    }
  }

  // Voiceover / captions preferences.
  if (NO_VOICEOVER_PATTERN.test(text)) result.voiceover = false;
  if (NO_CAPTION_PATTERN.test(text)) result.captions = false;

  // CTA in quotes.
  const ctaMatch = text.match(CTA_PATTERN);
  if (ctaMatch) result.cta = ctaMatch[1] || ctaMatch[2];

  // Language hint: presence of Bangla script vs. Latin-only.
  const hasBangla = /[ঀ-৿]/.test(text);
  result.language = hasBangla ? "bn" : result.language;

  return result;
}

/** Determines which single field is still missing, in the suggested priority order. */
export function nextMissingField(
  input: CreativeInput,
): "intent" | "assets" | "campaignType" | "style" | "duration" | "platform" | undefined {
  if (!input.businessName && !input.productCategory && !input.businessType) return "intent";
  if (!input.campaignType) return "campaignType";
  if (!input.style || input.style.length === 0) return "style";
  if (!input.duration) return "duration";
  if (!input.platform) return "platform";
  return undefined;
}
