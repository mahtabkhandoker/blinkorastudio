"use client";

import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import type { UploadedAsset } from "@/lib/chat/types";
import { CheckCircleIcon, AlertTriangleIcon, XCircleIcon } from "@/components/ui/icons";

const STATUS_ICON: Record<UploadedAsset["status"], ReactNode> = {
  UPLOADING: null,
  PROCESSING: null,
  VALID: <CheckCircleIcon className="h-3.5 w-3.5 text-emerald-600" />,
  WARNING: <AlertTriangleIcon className="h-3.5 w-3.5 text-amber-600" />,
  REJECTED: <XCircleIcon className="h-3.5 w-3.5 text-red-600" />,
};

export function AssetCard({ asset }: { asset: UploadedAsset }) {
  const t = useTranslations("chat");

  const statusLabel =
    asset.status === "UPLOADING"
      ? "Uploading..."
      : asset.status === "PROCESSING"
        ? t("checkingImage")
        : asset.status === "VALID"
          ? "Ready"
          : asset.status === "WARNING"
            ? "Needs attention"
            : "Rejected";

  const isBusy = asset.status === "UPLOADING" || asset.status === "PROCESSING";

  return (
    <div className="w-56 shrink-0 overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
      <div className="relative h-32 w-full bg-neutral-100 dark:bg-neutral-800">
        {asset.url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={asset.url}
            alt={asset.name}
            className={`h-full w-full object-cover ${isBusy ? "opacity-50" : ""}`}
          />
        )}
        {isBusy && (
          <div className="absolute inset-0 flex items-center justify-center" aria-live="polite">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-white/60 border-t-white" />
          </div>
        )}
      </div>
      <div className="px-3 py-2">
        <p className="truncate text-xs font-medium text-neutral-800 dark:text-neutral-200">
          {asset.name}
        </p>
        {asset.width && asset.height && (
          <p className="text-[11px] text-neutral-400">
            {asset.width} × {asset.height}
          </p>
        )}
        <p className="mt-1 flex items-center gap-1 text-[11px] font-medium text-neutral-500 dark:text-neutral-400">
          {STATUS_ICON[asset.status]}
          {statusLabel}
        </p>
      </div>
    </div>
  );
}
