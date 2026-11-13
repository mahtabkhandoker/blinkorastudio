"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  OrderApiError,
  createOrderApi,
  type AssetPurpose,
  type FormatChoice,
  type Locale,
  type OrderApiErrorKind,
  type OrderOptionsView,
  type OrderView,
} from "@/lib/api/orders";
import { forgetOrder, rememberOrder } from "./order-index";

/**
 * Drives the order screen. It holds the last `OrderView` the backend sent
 * and forwards the customer's input; it never decides what comes next and
 * never invents an order when the backend is down.
 */

export type OrderPhase = "loading" | "ready" | "unavailable" | "not_found";

export type OrderActionError = {
  kind: OrderApiErrorKind | "file_type" | "file_size";
  code: string | null;
  /** Localized sentence from the backend, if it sent one. */
  message: string | null;
};

export type PendingUpload = { name: string; previewUrl: string; purpose: AssetPurpose };

const POLL_MS = 2000;

function toActionError(error: unknown): OrderActionError {
  if (error instanceof OrderApiError) {
    return { kind: error.kind, code: error.code, message: error.userMessage };
  }
  return { kind: "unexpected", code: null, message: null };
}

export function useOrderController(params: {
  apiUrl: string;
  locale: Locale;
  orderId: string | null;
  customerRef?: string;
  onOrderCreated: (orderId: string) => void;
}) {
  const { apiUrl, locale, orderId, customerRef, onOrderCreated } = params;
  const api = useMemo(() => createOrderApi(apiUrl, locale), [apiUrl, locale]);

  const [phase, setPhase] = useState<OrderPhase>("loading");
  const [options, setOptions] = useState<OrderOptionsView | null>(null);
  const [order, setOrder] = useState<OrderView | null>(null);
  const [draftFormat, setDraftFormat] = useState<FormatChoice>("reels");
  const [busy, setBusy] = useState(false);
  const [pendingUpload, setPendingUpload] = useState<PendingUpload | null>(null);
  const [error, setError] = useState<OrderActionError | null>(null);
  const [editingCode, setEditingCode] = useState<string | null>(null);
  const [loadAttempt, setLoadAttempt] = useState(0);

  // The id of an order created during this visit. The URL catches up a
  // moment later; this keeps the load effect from refetching in between.
  const createdIdRef = useRef<string | null>(null);

  const accept = useCallback((view: OrderView) => {
    setOrder(view);
    rememberOrder(view);
  }, []);

  // ---- Initial load (and reload when the order id or locale changes) ----
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const skipOrder = !orderId || orderId === createdIdRef.current;
        const [nextOptions, nextOrder] = await Promise.all([
          api.getOptions(),
          skipOrder ? Promise.resolve(null) : api.getOrder(orderId),
        ]);
        if (cancelled) return;
        setOptions(nextOptions);
        if (nextOrder) accept(nextOrder);
        else if (!orderId) setOrder(null);
        setPhase("ready");
      } catch (caught) {
        if (cancelled) return;
        const mapped = toActionError(caught);
        if (mapped.kind === "not_found" && orderId) {
          forgetOrder(orderId);
          setPhase("not_found");
        } else {
          setPhase("unavailable");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [api, orderId, accept, loadAttempt]);

  const retryLoad = useCallback(() => {
    setPhase("loading");
    setLoadAttempt((n) => n + 1);
  }, []);

  // ---- Actions ----------------------------------------------------------
  const run = useCallback(
    async (action: () => Promise<OrderView>): Promise<boolean> => {
      setBusy(true);
      setError(null);
      try {
        accept(await action());
        setEditingCode(null);
        return true;
      } catch (caught) {
        const mapped = toActionError(caught);
        setError(mapped);
        // On a conflict the server's copy has moved on: show that copy.
        if (mapped.kind === "conflict" && order) {
          try {
            accept(await api.getOrder(order.id));
          } catch {
            // Leave the conflict message in place.
          }
        }
        return false;
      } finally {
        setBusy(false);
      }
    },
    [accept, api, order],
  );

  const ensureOrder = useCallback(async (): Promise<OrderView> => {
    if (order) return order;
    const created = await api.createOrder({ format: draftFormat, customer_ref: customerRef });
    createdIdRef.current = created.id;
    accept(created);
    onOrderCreated(created.id);
    return created;
  }, [accept, api, customerRef, draftFormat, onOrderCreated, order]);

  const setFormat = useCallback(
    (format: FormatChoice) => {
      if (!order) {
        setDraftFormat(format);
        return;
      }
      void run(() => api.setFormat(order.id, format));
    },
    [api, order, run],
  );

  const uploadFile = useCallback(
    async (file: File, purpose: AssetPurpose) => {
      const accepted = options?.accepted_mime_types ?? ["image/jpeg", "image/png", "image/webp"];
      const maxBytes = (options?.max_upload_mb ?? 10) * 1024 * 1024;
      // Quick feedback only; the backend re-checks the actual bytes.
      if (!accepted.includes(file.type)) {
        setError({ kind: "file_type", code: null, message: null });
        return;
      }
      if (file.size > maxBytes) {
        setError({ kind: "file_size", code: null, message: null });
        return;
      }
      const previewUrl = URL.createObjectURL(file);
      setPendingUpload({ name: file.name, previewUrl, purpose });
      try {
        await run(async () => {
          const target = await ensureOrder();
          return api.uploadAsset(target.id, file, purpose);
        });
      } finally {
        URL.revokeObjectURL(previewUrl);
        setPendingUpload(null);
      }
    },
    [api, ensureOrder, options, run],
  );

  const answer = useCallback(
    (code: string, value: string | null, skip = false) => {
      if (!order) return;
      void run(() => api.answer(order.id, code, value, skip));
    },
    [api, order, run],
  );

  const requestPlanChange = useCallback(() => {
    if (!order) return;
    void run(() => api.requestPlanChange(order.id));
  }, [api, order, run]);

  const confirmPlan = useCallback(() => {
    if (!order?.plan) return;
    const revision = order.plan.revision;
    void run(() => api.confirmPlan(order.id, revision));
  }, [api, order, run]);

  // ---- Poll while a generation is running --------------------------------
  const generationStatus = order?.generation?.status;
  const activeOrderId = order?.id;
  useEffect(() => {
    if (!activeOrderId || (generationStatus !== "QUEUED" && generationStatus !== "RUNNING")) return;
    const timer = setInterval(async () => {
      try {
        accept(await api.getOrder(activeOrderId));
      } catch {
        // Keep the last known status; the next tick tries again.
      }
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [accept, activeOrderId, api, generationStatus]);

  return {
    api,
    phase,
    options,
    order,
    format: order?.format ?? (options ? { ...options.format, value: draftFormat } : null),
    busy,
    pendingUpload,
    error,
    editingCode,
    startEditing: setEditingCode,
    cancelEditing: () => setEditingCode(null),
    dismissError: () => setError(null),
    retryLoad,
    setFormat,
    uploadFile,
    answer,
    requestPlanChange,
    confirmPlan,
  };
}

export type OrderController = ReturnType<typeof useOrderController>;
