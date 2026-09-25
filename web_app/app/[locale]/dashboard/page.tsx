"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { useAuth } from "@/lib/auth/auth-context";
import { usePackage } from "@/lib/package/package-context";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { PlusIcon, VideoIcon, CreditIcon } from "@/components/ui/icons";
import { listConversations } from "@/lib/chat/conversation-store";
import type { ConversationSummary } from "@/lib/chat/types";

const STATUS_TONE: Record<ConversationSummary["status"], "info" | "warning" | "success" | "danger"> = {
  active: "info",
  generating: "warning",
  completed: "success",
  failed: "danger",
};

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const { user } = useAuth();
  const { pkg } = usePackage();
  const [conversations] = useState<ConversationSummary[]>(() => listConversations());

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8 md:px-8">
      <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
        {t("welcomeBack", { name: user?.name ?? "" })}
      </h1>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <Link
          href="/dashboard/create"
          className="group flex flex-col justify-between rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md dark:border-neutral-800 dark:bg-neutral-900"
        >
          <div>
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-white">
              <PlusIcon className="h-5 w-5" />
            </div>
            <h2 className="text-base font-semibold text-neutral-900 dark:text-neutral-100">
              {t("createVideo")}
            </h2>
            <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
              {t("createVideoDesc")}
            </p>
          </div>
          <span className="mt-4 text-sm font-medium text-indigo-600 group-hover:underline">
            {t("createVideo")} →
          </span>
        </Link>

        <div className="rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
          <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-neutral-900 text-white dark:bg-white dark:text-neutral-900">
            <CreditIcon className="h-5 w-5" />
          </div>
          <h2 className="text-base font-semibold text-neutral-900 dark:text-neutral-100">
            {t("packageTitle")}
          </h2>
          {pkg && (
            <>
              <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                {pkg.planName} · {t("videosRemaining", { count: pkg.videosRemaining })}
              </p>
              <Link
                href="/dashboard/packages"
                className="mt-4 inline-block text-sm font-medium text-indigo-600 hover:underline"
              >
                {t("viewPackages")} →
              </Link>
            </>
          )}
        </div>
      </div>

      <div className="mt-10">
        <h2 className="mb-3 text-sm font-semibold text-neutral-700 dark:text-neutral-300">
          {t("recentProjects")}
        </h2>

        {conversations.length === 0 ? (
          <div className="rounded-xl border border-dashed border-neutral-300 p-8 text-center text-sm text-neutral-500 dark:border-neutral-700 dark:text-neutral-400">
            {t("noProjects")}
          </div>
        ) : (
          <ul className="divide-y divide-neutral-200 rounded-xl border border-neutral-200 bg-white dark:divide-neutral-800 dark:border-neutral-800 dark:bg-neutral-900">
            {conversations.map((c) => (
              <li key={c.id}>
                <Link
                  href={`/dashboard/create?c=${c.id}`}
                  className="flex items-center justify-between gap-3 px-4 py-3 hover:bg-neutral-50 dark:hover:bg-neutral-800"
                >
                  <span className="flex items-center gap-2.5 text-sm text-neutral-800 dark:text-neutral-200">
                    <VideoIcon className="h-4 w-4 shrink-0 text-neutral-400" />
                    {c.title}
                  </span>
                  <Badge tone={STATUS_TONE[c.status]}>{t(`status.${c.status}`)}</Badge>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>

      <p className="mt-8 text-xs text-neutral-400">
        <Button variant="ghost" size="sm" disabled>
          {t("nav.brand")}, {t("nav.settings")} — coming soon
        </Button>
      </p>
    </div>
  );
}
