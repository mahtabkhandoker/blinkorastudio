"use client";

import { useTranslations } from "next-intl";

export function ComingSoon({ titleKey }: { titleKey: string }) {
  const t = useTranslations("dashboard");
  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-16 text-center md:px-8">
      <h1 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
        {t(titleKey)}
      </h1>
      <p className="mt-2 text-sm text-neutral-500 dark:text-neutral-400">
        This section is coming soon.
      </p>
    </div>
  );
}
