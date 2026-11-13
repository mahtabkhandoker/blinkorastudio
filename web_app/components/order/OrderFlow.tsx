"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { AssistantMessage } from "@/components/chat/AssistantMessage";
import { UserMessage } from "@/components/chat/UserMessage";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { AlertTriangleIcon, CheckCircleIcon, ImageIcon, RefreshIcon, SendIcon } from "@/components/ui/icons";
import type {
  AnsweredView,
  AssetPurpose,
  AssetView,
  FormatChoice,
  FormatView,
  GenerationStatus,
  OrderView,
  QuestionView,
} from "@/lib/api/orders";
import type { OrderController, PendingUpload } from "@/lib/order/use-order-controller";

type T = ReturnType<typeof useTranslations>;

const CARD =
  "rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm dark:border-neutral-800 dark:bg-neutral-900";

/**
 * The order screen. Everything shown here comes from the backend's
 * `OrderView`: this component renders the current step and sends the
 * customer's input back. It contains no workflow rules of its own.
 */
export function OrderFlow({ controller }: { controller: OrderController }) {
  const t = useTranslations("order");
  const { phase, order, format, options, busy, error, pendingUpload, editingCode } = controller;
  const bottomRef = useRef<HTMLDivElement>(null);

  const stepKey = order ? `${order.step.kind}:${order.step.question?.code ?? ""}:${order.answered.length}` : "none";
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [stepKey, order?.generation?.status]);

  if (phase === "loading") {
    return (
      <Shell>
        <p className="py-10 text-center text-sm text-neutral-500" aria-live="polite">
          {t("loading")}
        </p>
      </Shell>
    );
  }

  if (phase === "unavailable") {
    return (
      <Shell>
        <StateCard
          tone="danger"
          title={t("unavailableTitle")}
          body={t("unavailableBody")}
          action={
            <Button size="sm" onClick={controller.retryLoad}>
              <RefreshIcon className="h-4 w-4" />
              {t("retry")}
            </Button>
          }
        />
      </Shell>
    );
  }

  if (phase === "not_found") {
    return (
      <Shell>
        <StateCard
          tone="warning"
          title={t("notFoundTitle")}
          body={t("notFoundBody")}
          action={
            <Link
              href="/dashboard/create"
              className="inline-flex rounded-lg bg-neutral-900 px-3 py-1.5 text-sm font-medium text-white dark:bg-white dark:text-neutral-900"
            >
              {t("startNew")}
            </Link>
          }
        />
      </Shell>
    );
  }

  const environment = order?.environment ?? options?.environment;
  const preConfirm = !order || order.status === "DRAFT" || order.status === "PLAN_READY";
  const step = order?.step;
  const collected = order ? order.answered.filter((a) => !isAfterPlan(a.code)) : [];
  const afterPlan = order ? order.answered.filter((a) => isAfterPlan(a.code) && !isFeedback(a.code)) : [];
  const feedback = order ? order.answered.filter((a) => isFeedback(a.code)) : [];
  const question = step?.kind === "question" ? step.question : null;
  const questionAfterPlan = question ? isAfterPlan(question.code) || question.code.startsWith("C2") : false;
  const photoStep = !order || step?.kind === "photo";

  const currentQuestion = question && !editingCode && (
    <QuestionPanel
      key={question.code}
      t={t}
      question={question}
      busy={busy}
      pendingUpload={pendingUpload}
      onAnswer={(value) => controller.answer(question.code, value)}
      onSkip={() => controller.answer(question.code, null, true)}
      onUpload={(file, purpose) => void controller.uploadFile(file, purpose)}
    />
  );

  const renderAnswered = (item: AnsweredView) =>
    editingCode === item.code ? (
      <QuestionPanel
        key={`edit-${item.code}`}
        t={t}
        question={item.question}
        busy={busy}
        pendingUpload={pendingUpload}
        selected={item.value}
        initialText={item.question.kind === "type" ? item.value : ""}
        onAnswer={(value) => controller.answer(item.code, value)}
        onSkip={() => controller.answer(item.code, null, true)}
        onUpload={(file, purpose) => void controller.uploadFile(file, purpose)}
        onCancel={controller.cancelEditing}
      />
    ) : (
      <AnsweredRow
        key={item.code}
        t={t}
        item={item}
        disabled={busy}
        onEdit={() => controller.startEditing(item.code)}
      />
    );

  return (
    <Shell>
      {environment?.simulated_generation && (
        <p
          className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200"
          role="note"
        >
          <AlertTriangleIcon className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          {environment.notice}
        </p>
      )}

      <section className={CARD} aria-label={t("setupLabel")}>
        {format && (
          <FormatToggle t={t} format={format} disabled={busy || !preConfirm} onChange={controller.setFormat} />
        )}
        <PhotoArea
          t={t}
          photos={order?.photos ?? []}
          assetUrl={controller.api.assetUrl}
          pendingUpload={pendingUpload?.purpose === "product" ? pendingUpload : null}
          prompt={photoStep ? (step?.message ?? options?.photo_prompt ?? "") : null}
          canUpload={preConfirm}
          busy={busy}
          maxMb={options?.max_upload_mb ?? 10}
          onFile={(file) => void controller.uploadFile(file, "product")}
        />
      </section>

      {collected.map(renderAnswered)}
      {!questionAfterPlan && currentQuestion}

      {order?.plan && step?.kind !== "photo" && (
        <AssistantMessage bare>
          <PlanCard
            t={t}
            order={order}
            busy={busy}
            actionable={step?.kind === "plan" && !editingCode}
            onConfirm={controller.confirmPlan}
            onChange={controller.requestPlanChange}
          />
        </AssistantMessage>
      )}

      {order?.generation && (
        <AssistantMessage bare>
          <GenerationCard t={t} order={order} />
        </AssistantMessage>
      )}

      {afterPlan.map(renderAnswered)}
      {feedback.map(renderAnswered)}
      {questionAfterPlan && currentQuestion}

      {order && step?.kind === "done" && (
        <AssistantMessage bare>
          <DoneCard t={t} order={order} />
        </AssistantMessage>
      )}

      {error && (
        <div
          role="alert"
          className="flex items-start justify-between gap-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200"
        >
          <span>{errorText(t, error, options?.max_upload_mb ?? 10)}</span>
          <button type="button" className="shrink-0 text-xs underline" onClick={controller.dismissError}>
            {t("dismiss")}
          </button>
        </div>
      )}

      <div ref={bottomRef} />
    </Shell>
  );
}

// ---- Helpers ------------------------------------------------------------------------

function isAfterPlan(code: string) {
  return code.startsWith("P") && !code.startsWith("PH_") ? true : isFeedback(code);
}

function isFeedback(code: string) {
  return code === "R1" || code === "R2";
}

function errorText(t: T, error: NonNullable<OrderController["error"]>, maxMb: number): string {
  if (error.message) return error.message;
  switch (error.kind) {
    case "unavailable":
      return t("errors.unavailable");
    case "conflict":
      return error.code === "PLAN_REVISION_STALE" ? t("errors.planChanged") : t("errors.conflict");
    case "not_found":
      return t("errors.notFound");
    case "file_type":
      return t("errors.fileType");
    case "file_size":
      return t("errors.fileSize", { mb: maxMb });
    case "invalid":
      return error.code === "INVALID_PHONE" ? t("errors.phone") : t("errors.invalid");
    default:
      return t("errors.generic");
  }
}

/** Digits in the reader's script (Bengali numerals for bn). */
function useLocalNumber() {
  const locale = useLocale();
  return (value: number) => new Intl.NumberFormat(locale, { useGrouping: false }).format(value);
}

function Shell({ children }: { children: ReactNode }) {
  return <div className="mx-auto w-full max-w-3xl flex-1 space-y-4 px-3 py-6 md:px-6">{children}</div>;
}

function StateCard({
  tone,
  title,
  body,
  action,
}: {
  tone: "danger" | "warning";
  title: string;
  body: string;
  action: ReactNode;
}) {
  const toneClass =
    tone === "danger"
      ? "border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950/40"
      : "border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/40";
  return (
    <div className={`rounded-2xl border p-5 ${toneClass}`} role="alert">
      <h2 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">{title}</h2>
      <p className="mt-1 text-sm text-neutral-700 dark:text-neutral-300">{body}</p>
      <div className="mt-4">{action}</div>
    </div>
  );
}

// ---- F1 · format ---------------------------------------------------------------------

function FormatToggle({
  t,
  format,
  disabled,
  onChange,
}: {
  t: T;
  format: FormatView;
  disabled: boolean;
  onChange: (format: FormatChoice) => void;
}) {
  return (
    <div>
      <p id="format-label" className="text-xs font-medium text-neutral-500 dark:text-neutral-400">
        {t("formatLabel")}
      </p>
      <div role="radiogroup" aria-labelledby="format-label" className="mt-2 flex flex-wrap gap-2">
        {format.options.map((option) => {
          const checked = option.id === format.value;
          const unavailable = !option.available;
          return (
            <button
              key={option.id}
              type="button"
              role="radio"
              aria-checked={checked}
              disabled={disabled || unavailable || !format.editable}
              onClick={() => !checked && onChange(option.id)}
              className={`rounded-xl border px-3.5 py-2 text-left text-sm transition-colors disabled:cursor-not-allowed ${
                checked
                  ? "border-indigo-600 bg-indigo-50 text-indigo-900 dark:bg-indigo-950/50 dark:text-indigo-100"
                  : "border-neutral-200 text-neutral-700 hover:border-neutral-400 disabled:opacity-50 dark:border-neutral-700 dark:text-neutral-200"
              }`}
            >
              <span className="block font-medium">{option.label}</span>
              <span className="block text-xs text-neutral-500 dark:text-neutral-400">
                {unavailable ? option.unavailable_reason : option.aspect_ratio}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ---- Product photo -------------------------------------------------------------------

function FileButton({
  label,
  disabled,
  variant = "secondary",
  onFile,
}: {
  label: string;
  disabled?: boolean;
  variant?: "primary" | "secondary";
  onFile: (file: File) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="sr-only"
        tabIndex={-1}
        aria-hidden
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          if (file) onFile(file);
        }}
      />
      <Button size="sm" variant={variant} disabled={disabled} onClick={() => inputRef.current?.click()}>
        <ImageIcon className="h-4 w-4" />
        {label}
      </Button>
    </>
  );
}

function PhotoArea({
  t,
  photos,
  assetUrl,
  pendingUpload,
  prompt,
  canUpload,
  busy,
  maxMb,
  onFile,
}: {
  t: T;
  photos: AssetView[];
  assetUrl: (asset: AssetView) => string;
  pendingUpload: PendingUpload | null;
  prompt: string | null;
  canUpload: boolean;
  busy: boolean;
  maxMb: number;
  onFile: (file: File) => void;
}) {
  const hasPhotos = photos.length > 0 || pendingUpload !== null;
  return (
    <div className="mt-4 border-t border-neutral-100 pt-4 dark:border-neutral-800">
      <p className="text-xs font-medium text-neutral-500 dark:text-neutral-400">{t("photoLabel")}</p>
      {prompt && <p className="mt-1 text-sm text-neutral-800 dark:text-neutral-100">{prompt}</p>}

      {hasPhotos && (
        <ul className="mt-3 flex flex-wrap gap-3">
          {photos.map((photo) => (
            <li key={photo.id} className="w-36">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={assetUrl(photo)}
                alt={photo.filename}
                className="h-36 w-36 rounded-xl border border-neutral-200 object-cover dark:border-neutral-700"
              />
              <p className="mt-1 flex items-center gap-1 text-[11px] text-neutral-500 dark:text-neutral-400">
                {photo.usable ? (
                  <CheckCircleIcon className="h-3.5 w-3.5 shrink-0 text-emerald-600" />
                ) : (
                  <AlertTriangleIcon className="h-3.5 w-3.5 shrink-0 text-amber-600" />
                )}
                <span>
                  {photo.width} × {photo.height} · {t("storedOnServer")}
                </span>
              </p>
            </li>
          ))}
          {pendingUpload && (
            <li className="w-36" aria-live="polite">
              <div className="relative h-36 w-36 overflow-hidden rounded-xl border border-neutral-200 dark:border-neutral-700">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={pendingUpload.previewUrl} alt="" className="h-full w-full object-cover opacity-50" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-neutral-400 border-t-neutral-900" />
                </div>
              </div>
              <p className="mt-1 text-[11px] text-neutral-500">{t("uploading")}</p>
            </li>
          )}
        </ul>
      )}

      {canUpload && (
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <FileButton
            label={photos.length > 0 && !prompt ? t("replacePhoto") : t("choosePhoto")}
            variant={photos.length > 0 && !prompt ? "secondary" : "primary"}
            disabled={busy}
            onFile={onFile}
          />
          <span className="text-xs text-neutral-400">{t("fileHint", { mb: maxMb })}</span>
        </div>
      )}
    </div>
  );
}

// ---- Questions -----------------------------------------------------------------------

function QuestionPanel({
  t,
  question,
  busy,
  pendingUpload,
  selected,
  initialText = "",
  onAnswer,
  onSkip,
  onUpload,
  onCancel,
}: {
  t: T;
  question: QuestionView;
  busy: boolean;
  pendingUpload: PendingUpload | null;
  selected?: string;
  initialText?: string;
  onAnswer: (value: string) => void;
  onSkip: () => void;
  onUpload: (file: File, purpose: AssetPurpose) => void;
  onCancel?: () => void;
}) {
  const [text, setText] = useState(initialText);
  const inputId = `answer-${question.code}`;
  const highlighted = selected ?? question.options.find((o) => o.default)?.id;

  return (
    <AssistantMessage>
      <div className="blinkora-message-in">
        <label htmlFor={question.kind === "type" ? inputId : undefined} className="block">
          {question.text}
        </label>

        {question.kind === "type" && (
          <form
            className="mt-2 flex flex-wrap items-center gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              if (text.trim()) onAnswer(text);
            }}
          >
            <input
              id={inputId}
              type={question.input_mode === "tel" ? "tel" : "text"}
              inputMode={question.input_mode === "tel" ? "tel" : "text"}
              autoComplete={question.input_mode === "tel" ? "tel" : "off"}
              value={text}
              maxLength={question.max_length ?? undefined}
              placeholder={question.placeholder ?? undefined}
              disabled={busy}
              autoFocus
              onChange={(event) => setText(event.target.value)}
              className="min-w-0 flex-1 rounded-xl border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 dark:border-neutral-700 dark:bg-neutral-950 dark:text-neutral-100"
            />
            <Button type="submit" size="sm" disabled={busy || !text.trim()} aria-label={t("send")}>
              <SendIcon className="h-4 w-4" />
            </Button>
          </form>
        )}

        {(question.options.length > 0 || question.kind === "upload" || question.skippable || onCancel) && (
          <div className="mt-2 flex flex-wrap gap-1.5" role="group" aria-label={question.text}>
            {question.kind === "upload" && question.upload_purpose && (
              <FileButton
                label={pendingUpload ? t("uploading") : (question.upload_label ?? t("choosePhoto"))}
                variant="primary"
                disabled={busy}
                onFile={(file) => onUpload(file, question.upload_purpose as AssetPurpose)}
              />
            )}
            {question.options.map((option) => (
              <button
                key={option.id}
                type="button"
                disabled={busy}
                aria-pressed={option.id === highlighted}
                onClick={() => onAnswer(option.id)}
                className={`rounded-full border px-3.5 py-1.5 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                  option.id === highlighted
                    ? "border-indigo-500 bg-indigo-50 text-indigo-900 dark:bg-indigo-950/50 dark:text-indigo-100"
                    : "border-neutral-200 bg-white text-neutral-700 hover:border-neutral-400 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-200"
                }`}
              >
                {option.label}
              </button>
            ))}
            {question.skippable && question.skip_label && (
              <button
                type="button"
                disabled={busy}
                onClick={onSkip}
                className="rounded-full px-3 py-1.5 text-sm text-neutral-500 underline-offset-2 hover:underline disabled:opacity-50 dark:text-neutral-400"
              >
                {question.skip_label}
              </button>
            )}
            {onCancel && (
              <button
                type="button"
                disabled={busy}
                onClick={onCancel}
                className="rounded-full px-3 py-1.5 text-sm text-neutral-500 hover:underline disabled:opacity-50"
              >
                {t("cancel")}
              </button>
            )}
          </div>
        )}
      </div>
    </AssistantMessage>
  );
}

function AnsweredRow({
  t,
  item,
  disabled,
  onEdit,
}: {
  t: T;
  item: AnsweredView;
  disabled: boolean;
  onEdit: () => void;
}) {
  return (
    <div className="space-y-2">
      <AssistantMessage>{item.question.text}</AssistantMessage>
      <UserMessage>{item.display}</UserMessage>
      {item.editable && (
        <div className="flex justify-end">
          <button
            type="button"
            disabled={disabled}
            onClick={onEdit}
            aria-label={`${t("change")}: ${item.question.text}`}
            className="text-xs text-neutral-500 underline-offset-2 hover:underline disabled:opacity-50 dark:text-neutral-400"
          >
            {t("change")}
          </button>
        </div>
      )}
    </div>
  );
}

// ---- C1 · plan -----------------------------------------------------------------------

function PlanCard({
  t,
  order,
  busy,
  actionable,
  onConfirm,
  onChange,
}: {
  t: T;
  order: OrderView;
  busy: boolean;
  actionable: boolean;
  onConfirm: () => void;
  onChange: () => void;
}) {
  const number = useLocalNumber();
  const plan = order.plan;
  if (!plan) return null;
  const failedChecks = order.eligibility?.checks.filter((c) => !c.ok) ?? [];
  const eligible = order.eligibility?.eligible ?? false;

  return (
    <div className={`${CARD} w-full max-w-lg`}>
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">{t("planTitle")}</h2>
        {plan.confirmed && <Badge tone="success">{t("planConfirmed")}</Badge>}
      </div>
      <p className="mt-2 text-sm text-neutral-700 dark:text-neutral-300">{plan.intro}</p>
      <ol className="mt-2 space-y-2">
        {plan.shots.map((shot) => (
          <li key={shot.index} className="flex gap-3 text-sm">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-neutral-100 text-xs font-semibold text-neutral-700 dark:bg-neutral-800 dark:text-neutral-200">
              {number(shot.index)}
            </span>
            <span className="text-neutral-900 dark:text-neutral-100">
              {shot.description}
              {shot.note && (
                <span className="mt-0.5 block text-xs text-amber-700 dark:text-amber-300">{shot.note}</span>
              )}
            </span>
          </li>
        ))}
      </ol>
      <p className="mt-3 text-xs text-neutral-500 dark:text-neutral-400">{plan.post_production_note}</p>

      {actionable && (
        <>
          {failedChecks.length > 0 && (
            <ul className="mt-3 space-y-1 text-xs text-red-700 dark:text-red-300" role="alert">
              {failedChecks.map((check) => (
                <li key={check.code}>✕ {check.message}</li>
              ))}
            </ul>
          )}
          <p className="mt-4 text-sm font-medium text-neutral-900 dark:text-neutral-100">{plan.closing}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <Button size="sm" disabled={busy || !eligible} onClick={onConfirm}>
              {plan.confirm_label}
            </Button>
            <Button size="sm" variant="secondary" disabled={busy} onClick={onChange}>
              {plan.change_label}
            </Button>
          </div>
        </>
      )}
    </div>
  );
}

// ---- Generation (simulated in this build) ------------------------------------------------

const STATUS_TONE: Record<GenerationStatus, "neutral" | "warning" | "success" | "danger"> = {
  QUEUED: "neutral",
  RUNNING: "warning",
  SUCCEEDED: "success",
  FAILED: "danger",
};

function GenerationCard({ t, order }: { t: T; order: OrderView }) {
  const number = useLocalNumber();
  const generation = order.generation;
  if (!generation) return null;
  return (
    <div className={`${CARD} w-full max-w-lg`} aria-live="polite">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">{t("generationTitle")}</h2>
        {generation.simulated && <Badge tone="warning">{t("simulatedTag")}</Badge>}
      </div>
      <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        <dt className="text-neutral-500 dark:text-neutral-400">{t("orderNumber")}</dt>
        <dd className="font-mono text-neutral-900 dark:text-neutral-100">{order.number}</dd>
        <dt className="text-neutral-500 dark:text-neutral-400">{t("generationId")}</dt>
        <dd className="font-mono text-neutral-900 dark:text-neutral-100">{generation.id}</dd>
      </dl>
      <ul className="mt-3 space-y-1.5">
        {generation.shots.map((shot) => (
          <li key={shot.index} className="flex items-center justify-between gap-3 text-sm">
            <span className="text-neutral-700 dark:text-neutral-300">{t("scene", { n: number(shot.index) })}</span>
            <Badge tone={STATUS_TONE[shot.status]}>{t(`generationStatus.${shot.status}`)}</Badge>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-sm text-neutral-800 dark:text-neutral-100">{generation.message}</p>
    </div>
  );
}

function DoneCard({ t, order }: { t: T; order: OrderView }) {
  const noGeneration = order.status === "CONFIRMED";
  return (
    <div className={`${CARD} w-full max-w-lg`}>
      <h2 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
        {t("doneTitle", { number: order.number })}
      </h2>
      <p className="mt-1 text-sm text-neutral-700 dark:text-neutral-300">
        {noGeneration ? t("doneNoGeneration") : order.feedback ? t("doneWithFeedback") : t("doneBody")}
      </p>
      <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        <dt className="text-neutral-500 dark:text-neutral-400">{t("brandName")}</dt>
        <dd className="text-neutral-900 dark:text-neutral-100">{order.brand.shop_name ?? "—"}</dd>
        <dt className="text-neutral-500 dark:text-neutral-400">{t("brandPhone")}</dt>
        <dd className="text-neutral-900 dark:text-neutral-100">{order.brand.phone ?? "—"}</dd>
        <dt className="text-neutral-500 dark:text-neutral-400">{t("brandLogo")}</dt>
        <dd className="text-neutral-900 dark:text-neutral-100">
          {order.brand.has_logo ? t("logoOnFile") : t("logoNone")}
        </dd>
      </dl>
      <Link
        href="/dashboard/create"
        className="mt-4 inline-flex rounded-lg border border-neutral-200 px-3 py-1.5 text-sm font-medium text-neutral-900 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-100 dark:hover:bg-neutral-800"
      >
        {t("startNew")}
      </Link>
    </div>
  );
}
