"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { Button } from "@/components/ui/Button";

export function PackageCheckCard({
  hasQuota,
  planName,
  videosRemaining,
  conversationId,
  onConfirm,
  disabled,
}: {
  hasQuota: boolean;
  planName?: string;
  videosRemaining?: number;
  conversationId: string;
  onConfirm: () => void;
  disabled?: boolean;
}) {
  const t = useTranslations("chat");

  if (!hasQuota) {
    return (
      <div className="w-full max-w-md rounded-2xl border border-amber-200 bg-amber-50/60 p-5 text-sm shadow-sm dark:border-amber-900 dark:bg-amber-950/30">
        <p className="font-medium text-neutral-900 dark:text-neutral-100">
          {t("packageCheck.noPackageTitle")}
        </p>
        <Link href={`/dashboard/packages?return=${conversationId}`} className="mt-3 inline-block">
          <Button size="sm">{t("packageCheck.viewPackages")}</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
      <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
        {t("packageCheck.title")}
      </h3>
      <dl className="mt-3 space-y-2 text-sm">
        <div className="flex justify-between">
          <dt className="text-neutral-500 dark:text-neutral-400">{t("packageCheck.package")}</dt>
          <dd className="text-neutral-800 dark:text-neutral-200">{planName}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-neutral-500 dark:text-neutral-400">{t("packageCheck.remaining")}</dt>
          <dd className="text-neutral-800 dark:text-neutral-200">{videosRemaining}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-neutral-500 dark:text-neutral-400">
            {t("packageCheck.thisGeneration")}
          </dt>
          <dd className="text-neutral-800 dark:text-neutral-200">{t("packageCheck.oneVideo")}</dd>
        </div>
      </dl>
      <Button size="sm" className="mt-4 w-full" onClick={onConfirm} disabled={disabled}>
        {t("packageCheck.confirm")}
      </Button>
    </div>
  );
}
