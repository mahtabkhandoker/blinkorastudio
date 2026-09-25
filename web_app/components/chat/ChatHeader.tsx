"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { Badge } from "@/components/ui/Badge";
import { MenuIcon } from "@/components/ui/icons";
import type { ConversationSummary } from "@/lib/chat/types";

const STATUS_TONE: Record<ConversationSummary["status"], "info" | "warning" | "success" | "danger"> = {
  active: "info",
  generating: "warning",
  completed: "success",
  failed: "danger",
};

export function ChatHeader({
  title,
  status,
  onToggleSidebar,
}: {
  title: string;
  status: ConversationSummary["status"];
  onToggleSidebar?: () => void;
}) {
  const t = useTranslations("dashboard");

  return (
    <header className="flex items-center gap-3 border-b border-neutral-200 bg-white/80 px-3 py-3 backdrop-blur dark:border-neutral-800 dark:bg-neutral-950/80 md:px-6">
      <button
        type="button"
        onClick={() => onToggleSidebar?.()}
        aria-label="Toggle chat history"
        className="rounded-lg p-1.5 text-neutral-600 hover:bg-neutral-100 lg:hidden dark:text-neutral-300 dark:hover:bg-neutral-800"
      >
        <MenuIcon className="h-5 w-5" />
      </button>
      <Link
        href="/dashboard"
        className="hidden text-sm text-neutral-400 hover:text-neutral-700 sm:inline dark:hover:text-neutral-200"
      >
        {t("title")}
      </Link>
      <span className="hidden text-neutral-300 sm:inline">/</span>
      <h1 className="truncate text-sm font-semibold text-neutral-900 dark:text-neutral-100">{title}</h1>
      <div className="ml-auto">
        <Badge tone={STATUS_TONE[status]}>{t(`status.${status}`)}</Badge>
      </div>
    </header>
  );
}
