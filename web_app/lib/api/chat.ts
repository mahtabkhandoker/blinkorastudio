/**
 * Thin client for the chatbot backend (`/api/chat/message`).
 *
 * This module ONLY talks to the backend and translates between the
 * frontend's camelCase `CreativeInput`/`UploadedAsset` shapes and the
 * backend's snake_case Pydantic schemas. It never decides workflow stage,
 * missing fields, or confirmation state itself — the backend's
 * `ChatOrchestrator` is the single source of truth for that (see
 * `backend/app/services/chatbot/orchestrator.py`). The frontend only
 * renders whatever the backend returns.
 *
 * When `NEXT_PUBLIC_CHAT_API_URL` is not set, or a request fails for any
 * reason (network error, non-2xx, timeout), `getChatApiUrl()` returns
 * `null` / `sendChatMessage` throws, and callers in
 * `use-chat-controller.ts` fall back to the existing local/mock engine
 * (`parse-input.ts` + the client-side state machine) — the chat keeps
 * working exactly as it did before this integration.
 */

import type { CreativeInput, CreationStage, MissingField, UploadedAsset } from "@/lib/chat/types";

// ---- Backend wire types (snake_case, mirrors backend/app/models) -----------

export type BackendCreativeInput = {
  business_name?: string | null;
  business_type?: string | null;
  product_name?: string | null;
  product_category?: string | null;
  campaign_type?: string | null;
  target_audience?: string | null;
  duration_seconds?: number | null;
  aspect_ratio?: string | null;
  platform?: string | null;
  style?: string[];
  language?: string | null;
  captions?: boolean | null;
  voiceover?: boolean | null;
  music_mood?: string | null;
  cta?: string | null;
  notes?: string | null;
};

export type BackendAssetInfo = {
  id: string;
  filename: string;
  mime_type?: string | null;
  status: UploadedAsset["status"];
  warning_code?: UploadedAsset["warningCode"] | null;
  warning_message?: string | null;
  width?: number | null;
  height?: number | null;
};

export type BackendMissingField = "product_name" | "campaign_type" | "duration_seconds" | "style";

export type ChatMessageResponse = {
  reply: string;
  stage: CreationStage;
  extracted: Record<string, unknown>;
  creative_input: BackendCreativeInput;
  missing_field: BackendMissingField | null;
  quick_replies: string[];
  brief_ready: boolean;
  requires_confirmation: boolean;
  creative_brief?: Record<string, unknown> | null;
  needs_assets?: boolean;
};

// ---- Config -----------------------------------------------------------------

/** Returns the configured backend base URL, or `null` when the backend
 * integration is disabled (the default — mock/local mode). */
export function getChatApiUrl(): string | null {
  const url = process.env.NEXT_PUBLIC_CHAT_API_URL;
  if (!url) return null;
  return url.replace(/\/+$/, "");
}

// ---- Field mapping ------------------------------------------------------------

const MISSING_FIELD_MAP: Record<BackendMissingField, MissingField> = {
  product_name: "intent",
  campaign_type: "campaignType",
  duration_seconds: "duration",
  style: "style",
};

export function mapMissingField(field: BackendMissingField | null): MissingField | undefined {
  return field ? MISSING_FIELD_MAP[field] : undefined;
}

export function toBackendCreativeInput(input: CreativeInput): BackendCreativeInput {
  return {
    business_name: input.businessName ?? null,
    business_type: input.businessType ?? null,
    product_name: input.productName ?? input.businessName ?? null,
    product_category: input.productCategory ?? null,
    campaign_type: input.campaignType ?? null,
    target_audience: input.targetAudience ?? null,
    duration_seconds: input.duration ?? null,
    aspect_ratio: input.aspectRatio ?? null,
    platform: input.platform ?? null,
    style: input.style ?? [],
    language: input.language ?? null,
    captions: input.captions ?? null,
    voiceover: input.voiceover ?? null,
    music_mood: input.musicMood ?? null,
    cta: input.cta ?? null,
  };
}

export function fromBackendCreativeInput(input: BackendCreativeInput): Partial<CreativeInput> {
  const patch: Partial<CreativeInput> = {};
  if (input.business_name != null) patch.businessName = input.business_name;
  if (input.business_type != null) patch.businessType = input.business_type;
  // The backend uses the business name as the product's identity too
  // (see rule_based_extract's comment); mirror that onto productName so
  // local fallback logic (which reads either field) stays consistent.
  if (input.product_name != null) patch.productName = input.product_name;
  if (input.product_category != null) patch.productCategory = input.product_category;
  if (input.campaign_type != null) patch.campaignType = input.campaign_type;
  if (input.target_audience != null) patch.targetAudience = input.target_audience;
  if (input.duration_seconds != null) patch.duration = input.duration_seconds;
  if (input.aspect_ratio != null) patch.aspectRatio = input.aspect_ratio as CreativeInput["aspectRatio"];
  if (input.platform != null) patch.platform = input.platform as CreativeInput["platform"];
  if (input.style != null && input.style.length > 0) {
    patch.style = input.style as CreativeInput["style"];
  }
  if (input.language != null) patch.language = input.language;
  if (input.captions != null) patch.captions = input.captions;
  if (input.voiceover != null) patch.voiceover = input.voiceover;
  if (input.music_mood != null) patch.musicMood = input.music_mood;
  if (input.cta != null) patch.cta = input.cta;
  return patch;
}

export function toBackendAssets(assets: UploadedAsset[]): BackendAssetInfo[] {
  return assets.map((asset) => ({
    id: asset.id,
    filename: asset.name,
    status: asset.status,
    warning_code: asset.warningCode ?? null,
    warning_message: asset.warningMessage ?? null,
    width: asset.width ?? null,
    height: asset.height ?? null,
  }));
}

// ---- Request ------------------------------------------------------------------

export type SendChatMessageParams = {
  apiUrl: string;
  conversationId: string;
  message: string;
  requestId: string;
  stage: CreationStage;
  creativeInput: CreativeInput;
  assets: UploadedAsset[];
  briefConfirmed: boolean;
  /** Aborts the request after this many ms so a stalled backend can't hang the chat. */
  timeoutMs?: number;
};

/** Never exposed to the UI: internal provider/model identifiers must not
 * leak past this module even in error messages. */
export async function sendChatMessage(params: SendChatMessageParams): Promise<ChatMessageResponse> {
  const {
    apiUrl,
    conversationId,
    message,
    requestId,
    stage,
    creativeInput,
    assets,
    briefConfirmed,
    timeoutMs = 15000,
  } = params;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${apiUrl}/api/chat/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify({
        conversation_id: conversationId,
        message,
        request_id: requestId,
        state: {
          stage,
          creative_input: toBackendCreativeInput(creativeInput),
          assets: toBackendAssets(assets),
          brief_confirmed: briefConfirmed,
        },
      }),
    });

    if (!response.ok) {
      throw new Error(`chat backend responded with status ${response.status}`);
    }

    return (await response.json()) as ChatMessageResponse;
  } finally {
    clearTimeout(timer);
  }
}
