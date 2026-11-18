/**
 * Typed client for the P0 order workflow API (`backend/app/api/routes/orders.py`).
 *
 * The backend owns the workflow: classification, which question comes
 * next, the creative plan and generation. This module only transports
 * requests and types the responses; it holds no business rules.
 *
 * There is deliberately no local fallback here. If the backend cannot be
 * reached, every call throws `OrderApiError` with kind "unavailable" and
 * the UI says so. A failed request must never turn into an order that
 * only exists in the browser.
 *
 * Types mirror `backend/app/models/orders.py` (the `*View` models).
 */

export type FormatChoice = "reels" | "post" | "both";
export type OrderStatus = "DRAFT" | "PLAN_READY" | "CONFIRMED" | "GENERATING" | "GENERATED" | "FAILED";
export type GenerationStatus = "QUEUED" | "RUNNING" | "SUCCEEDED" | "FAILED";
export type QuestionKind = "choose" | "type" | "upload";
export type AssetPurpose = "product" | "logo";
export type Locale = "bn" | "en";

export type OptionView = { id: string; label: string; default: boolean };

export type QuestionView = {
  code: string;
  kind: QuestionKind;
  text: string;
  options: OptionView[];
  placeholder: string | null;
  input_mode: "text" | "tel";
  max_length: number | null;
  skippable: boolean;
  skip_label: string | null;
  upload_purpose: AssetPurpose | null;
  upload_label: string | null;
};

export type AnsweredView = {
  code: string;
  question: QuestionView;
  value: string;
  display: string;
  source: "customer" | "default";
  editable: boolean;
};

export type AssetView = {
  id: string;
  purpose: AssetPurpose;
  filename: string;
  width: number;
  height: number;
  status: "VALID" | "WARNING";
  warning_code: string | null;
  message: string | null;
  usable: boolean;
  /** Path on the backend that serves the stored file. Not a blob: URL. */
  content_path: string;
};

export type FormatOptionView = {
  id: FormatChoice;
  label: string;
  aspect_ratio: string;
  available: boolean;
  unavailable_reason: string | null;
};

export type FormatView = { value: FormatChoice; editable: boolean; options: FormatOptionView[] };

export type StepView = {
  kind: "photo" | "question" | "plan" | "generation" | "done";
  message: string | null;
  question: QuestionView | null;
  photo: { reason: "initial" | "more_photos"; required_count: number; have_count: number } | null;
};

export type PlanView = {
  revision: number;
  intro: string;
  shots: { index: number; description: string; note: string | null; generates_video: boolean }[];
  closing: string;
  post_production_note: string;
  confirm_label: string;
  change_label: string;
  confirmed: boolean;
};

export type EligibilityView = {
  eligible: boolean;
  checks: { code: string; ok: boolean; message: string }[];
};

export type GenerationView = {
  id: string;
  status: GenerationStatus;
  simulated: boolean;
  plan_revision: number;
  shots: { index: number; status: GenerationStatus }[];
  message: string;
  deduplicated: boolean;
};

export type EnvironmentView = {
  video_provider: string;
  simulated_generation: boolean;
  storage: string;
  notice: string;
};

export type OrderView = {
  id: string;
  number: string;
  title: string;
  channel: "web" | "whatsapp";
  locale: Locale;
  status: OrderStatus;
  format: FormatView;
  photos: AssetView[];
  logo: AssetView | null;
  answered: AnsweredView[];
  step: StepView;
  plan: PlanView | null;
  eligibility: EligibilityView | null;
  generation: GenerationView | null;
  brand: { shop_name: string | null; phone: string | null; has_logo: boolean };
  feedback: { rating: string; scene: string | null; generation_id: string | null } | null;
  environment: EnvironmentView;
};

export type OrderSummaryView = {
  id: string;
  number: string;
  title: string;
  status: OrderStatus;
  updated_at: string;
};

export type OrderOptionsView = {
  format: FormatView;
  max_upload_mb: number;
  accepted_mime_types: string[];
  photo_prompt: string;
  environment: EnvironmentView;
};

// ---- Errors ----------------------------------------------------------------------

export type OrderApiErrorKind =
  | "unavailable" // network failure, timeout or 5xx: nothing was saved
  | "not_found" // the order is not on the server
  | "conflict" // the order moved on (stale plan, already confirmed, ...)
  | "invalid" // the input was rejected (bad file, bad phone number, ...)
  | "unauthorized" // no/expired session — the UI should send the seller to /login
  | "unexpected";

export class OrderApiError extends Error {
  readonly kind: OrderApiErrorKind;
  readonly code: string | null;
  /** A localized sentence from the backend, when it sent one. */
  readonly userMessage: string | null;
  readonly status: number | null;

  constructor(kind: OrderApiErrorKind, options: { code?: string | null; userMessage?: string | null; status?: number | null; detail?: string } = {}) {
    super(options.detail ?? options.code ?? kind);
    this.name = "OrderApiError";
    this.kind = kind;
    this.code = options.code ?? null;
    this.userMessage = options.userMessage ?? null;
    this.status = options.status ?? null;
  }
}

export function kindForStatus(status: number): OrderApiErrorKind {
  if (status === 401 || status === 403) return "unauthorized";
  if (status === 404) return "not_found";
  if (status === 409) return "conflict";
  if (status === 400 || status === 413 || status === 422) return "invalid";
  if (status >= 500) return "unavailable";
  return "unexpected";
}

const CSRF_COOKIE_NAME = "blinkora_csrf";

function readCsrfCookie(): string | null {
  if (typeof document === "undefined") return null;
  const prefix = `${CSRF_COOKIE_NAME}=`;
  for (const part of document.cookie.split(";")) {
    const trimmed = part.trim();
    if (trimmed.startsWith(prefix)) return decodeURIComponent(trimmed.slice(prefix.length));
  }
  return null;
}

// ---- Config ----------------------------------------------------------------------

/** Base URL of the backend, or null when none is configured. */
export function getOrderApiUrl(): string | null {
  const url = process.env.NEXT_PUBLIC_CHAT_API_URL;
  if (!url) return null;
  return url.replace(/\/+$/, "");
}

/** Deterministic per plan revision, so a retried tap reuses the same key. */
export function confirmIdempotencyKey(orderId: string, planRevision: number): string {
  return `${orderId}:rev${planRevision}`;
}

// ---- Client ----------------------------------------------------------------------

type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

export type OrderApi = ReturnType<typeof createOrderApi>;

export function createOrderApi(baseUrl: string, locale: Locale, fetchImpl: FetchLike = fetch, timeoutMs = 20000) {
  const base = baseUrl.replace(/\/+$/, "");

  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const separator = path.includes("?") ? "&" : "?";
    const method = (init.method ?? "GET").toUpperCase();
    const headers: Record<string, string> = { ...(init.headers as Record<string, string> | undefined) };
    if (method !== "GET" && method !== "HEAD") {
      const csrf = readCsrfCookie();
      if (csrf) headers["X-CSRF-Token"] = csrf;
    }
    let response: Response;
    try {
      response = await fetchImpl(`${base}${path}${separator}locale=${locale}`, {
        ...init,
        method,
        headers,
        credentials: "include",
        signal: controller.signal,
      });
    } catch (error) {
      throw new OrderApiError("unavailable", { detail: error instanceof Error ? error.message : "network error" });
    } finally {
      clearTimeout(timer);
    }

    if (!response.ok) {
      let body: { error_code?: string; detail?: unknown; message?: string | null } = {};
      try {
        body = await response.json();
      } catch {
        // A non-JSON error body (proxy page, crash) carries nothing usable.
      }
      throw new OrderApiError(kindForStatus(response.status), {
        code: body.error_code ?? null,
        userMessage: body.message ?? null,
        status: response.status,
        detail: typeof body.detail === "string" ? body.detail : undefined,
      });
    }

    try {
      return (await response.json()) as T;
    } catch {
      throw new OrderApiError("unavailable", { detail: "The backend returned an unreadable response." });
    }
  }

  const json = (method: string, body?: unknown, headers: Record<string, string> = {}): RequestInit => ({
    method,
    headers: { "Content-Type": "application/json", ...headers },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  return {
    baseUrl: base,

    assetUrl(asset: Pick<AssetView, "content_path">): string {
      return `${base}${asset.content_path}`;
    },

    getOptions: () => request<OrderOptionsView>("/api/orders/options"),

    /** The signed-in seller's own orders, newest first — backs "My Orders". */
    listOrders: () => request<OrderSummaryView[]>("/api/orders"),

    createOrder: (body: { format: FormatChoice; customer_ref?: string }) =>
      request<OrderView>("/api/orders", json("POST", { channel: "web", locale, ...body })),

    getOrder: (orderId: string) => request<OrderView>(`/api/orders/${orderId}`),

    setFormat: (orderId: string, format: FormatChoice) =>
      request<OrderView>(`/api/orders/${orderId}/format`, json("PUT", { format })),

    uploadAsset(orderId: string, file: File, purpose: AssetPurpose) {
      const form = new FormData();
      form.append("file", file);
      form.append("purpose", purpose);
      return request<OrderView>(`/api/orders/${orderId}/assets`, { method: "POST", body: form });
    },

    answer: (orderId: string, code: string, value: string | null, skip = false) =>
      request<OrderView>(`/api/orders/${orderId}/answers`, json("POST", { code, value, skip })),

    requestPlanChange: (orderId: string) => request<OrderView>(`/api/orders/${orderId}/plan/change`, json("POST")),

    confirmPlan: (orderId: string, planRevision: number) =>
      request<OrderView>(
        `/api/orders/${orderId}/plan/confirm`,
        json("POST", { plan_revision: planRevision }, { "Idempotency-Key": confirmIdempotencyKey(orderId, planRevision) }),
      ),
  };
}
