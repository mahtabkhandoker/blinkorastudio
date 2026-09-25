"use client";

import { useTranslations } from "next-intl";
import type { UploadedAsset } from "@/lib/chat/types";
import { Button } from "@/components/ui/Button";
import { CheckCircleIcon, AlertTriangleIcon, XCircleIcon } from "@/components/ui/icons";

export function AssetValidationCard({
  asset,
  onReplace,
  onContinueAnyway,
}: {
  asset: UploadedAsset;
  onReplace: () => void;
  onContinueAnyway: () => void;
}) {
  const t = useTranslations("chat");

  if (asset.status === "PROCESSING" || asset.status === "UPLOADING") {
    return (
      <div
        className="flex w-full max-w-md items-center gap-2.5 rounded-xl border border-neutral-200 bg-white px-4 py-3 text-sm text-neutral-500 shadow-sm dark:border-neutral-800 dark:bg-neutral-900 dark:text-neutral-400"
        aria-live="polite"
      >
        <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-600 dark:border-neutral-700 dark:border-t-neutral-300" />
        {t("checkingImage")}
      </div>
    );
  }

  const tone =
    asset.status === "VALID" ? "success" : asset.status === "WARNING" ? "warning" : "danger";

  const icon =
    tone === "success" ? (
      <CheckCircleIcon className="h-5 w-5 text-emerald-600" />
    ) : tone === "warning" ? (
      <AlertTriangleIcon className="h-5 w-5 text-amber-600" />
    ) : (
      <XCircleIcon className="h-5 w-5 text-red-600" />
    );

  const containerTone =
    tone === "success"
      ? "border-emerald-200 bg-emerald-50/60 dark:border-emerald-900 dark:bg-emerald-950/30"
      : tone === "warning"
        ? "border-amber-200 bg-amber-50/60 dark:border-amber-900 dark:bg-amber-950/30"
        : "border-red-200 bg-red-50/60 dark:border-red-900 dark:bg-red-950/30";

  return (
    <div
      className={`w-full max-w-md rounded-xl border px-4 py-3 shadow-sm ${containerTone}`}
      role="status"
      aria-live="polite"
    >
      <div className="flex items-start gap-2.5">
        <div className="mt-0.5 shrink-0">{icon}</div>
        <p className="text-sm text-neutral-800 dark:text-neutral-100">{asset.warningMessage}</p>
      </div>

      {tone === "warning" && (
        <div className="mt-3 flex flex-wrap gap-2">
          <Button size="sm" variant="secondary" onClick={onReplace}>
            {t("replaceImage")}
          </Button>
          <Button size="sm" variant="ghost" onClick={onContinueAnyway}>
            {t("continueAnyway")}
          </Button>
        </div>
      )}

      {tone === "danger" && (
        <div className="mt-3">
          <Button size="sm" variant="secondary" onClick={onReplace}>
            {t("uploadAnother")}
          </Button>
        </div>
      )}
    </div>
  );
}
