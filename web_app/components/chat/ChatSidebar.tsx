"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { LogoMark, PlusIcon } from "@/components/ui/icons";
import type { ConversationSummary } from "@/lib/chat/types";

const STATUS_DOT: Record<ConversationSummary["status"], string> = {
  active: "●",
  generating: "◌",
  completed: "✓",
  failed: "!",
};

const STATUS_COLOR: Record<ConversationSummary["status"], string> = {
  active: "text-indigo-500",
  generating: "text-amber-500 animate-pulse",
  completed: "text-emerald-500",
  failed: "text-red-500",
};

export function ChatSidebar({
  conversations,
  activeId,
}: {
  conversations: ConversationSummary[];
  activeId: string;
}) {
  const t = useTranslations("chat");
  const tApp = useTranslations("app");

  return (
    <aside className="flex h-full w-full flex-col border-r border-neutral-200 bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-950">
      <div className="flex items-center gap-2 px-4 py-4">
        <LogoMark className="h-6 w-6 text-indigo-600" />
        <span className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
          {tApp("name")}
        </span>
      </div>

      <div className="px-3">
        <Link
          href="/dashboard/create"
          className="flex items-center gap-2 rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm font-medium text-neutral-800 hover:bg-neutral-50 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-100 dark:hover:bg-neutral-800"
        >
          <PlusIcon className="h-4 w-4" />
          {t("newVideo")}
        </Link>
      </div>

      <div className="mt-4 flex-1 overflow-y-auto px-2 pb-4">
        <p className="px-2 pb-1.5 text-xs font-medium uppercase tracking-wide text-neutral-400">
          {t("recentChats")}
        </p>
        {conversations.length === 0 ? (
          <p className="px-2 py-2 text-sm text-neutral-400">{t("noChats")}</p>
        ) : (
          <ul className="space-y-0.5">
            {conversations.map((c) => (
              <li key={c.id}>
                <Link
                  href={`/dashboard/create?c=${c.id}`}
                  aria-current={c.id === activeId ? "page" : undefined}
                  className={`flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm ${
                    c.id === activeId
                      ? "bg-neutral-200/70 font-medium text-neutral-900 dark:bg-neutral-800 dark:text-neutral-100"
                      : "text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-900"
                  }`}
                >
                  <span className={`text-xs ${STATUS_COLOR[c.status]}`} aria-hidden>
                    {STATUS_DOT[c.status]}
                  </span>
                  <span className="truncate">{c.title}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
