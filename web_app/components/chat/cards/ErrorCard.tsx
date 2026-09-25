"use client";

import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/Button";
import { AlertTriangleIcon } from "@/components/ui/icons";

export function ErrorCard({
  text,
  retryable,
  onRetry,
}: {
  text: string;
  retryable?: boolean;
  onRetry?: () => void;
}) {
  const t = useTranslations("chat");
  return (
    <div
      className="flex w-full max-w-md items-start gap-2.5 rounded-xl border border-red-200 bg-red-50/60 px-4 py-3 shadow-sm dark:border-red-900 dark:bg-red-950/30"
      role="alert"
    >
      <AlertTriangleIcon className="mt-0.5 h-5 w-5 shrink-0 text-red-600" />
      <div className="flex-1">
        <p className="text-sm text-neutral-800 dark:text-neutral-100">{text}</p>
        {retryable && onRetry && (
          <Button size="sm" variant="secondary" className="mt-2" onClick={onRetry}>
            {t("errors.retry")}
          </Button>
        )}
      </div>
    </div>
  );
}
