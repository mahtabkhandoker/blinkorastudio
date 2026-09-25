"use client";

import { useTranslations } from "next-intl";
import type { GenerationStageKey, GenerationState } from "@/lib/chat/types";

const STAGE_ORDER: GenerationStageKey[] = [
  "PREPARING",
  "GENERATING",
  "VALIDATING",
  "FINALIZING",
];

function stageIndex(status: GenerationStageKey): number {
  if (status === "QUEUED") return -1;
  if (status === "COMPLETED") return STAGE_ORDER.length;
  return STAGE_ORDER.indexOf(status);
}

export function GenerationStatusCard({ generation }: { generation: GenerationState }) {
  const t = useTranslations("chat");
  const currentIndex = stageIndex(generation.status);

  return (
    <div
      className="w-full max-w-md rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm dark:border-neutral-800 dark:bg-neutral-900"
      aria-live="polite"
      role="status"
    >
      <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
        {generation.isRevision ? t("brief.title") : t("generating")}
      </h3>

      <ul className="mt-3 space-y-2">
        {STAGE_ORDER.map((stage, index) => {
          const done = currentIndex > index || generation.status === "COMPLETED";
          const active = currentIndex === index;
          return (
            <li key={stage} className="flex items-center gap-2.5 text-sm">
              <span
                className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[10px] ${
                  done
                    ? "bg-emerald-500 text-white"
                    : active
                      ? "border-2 border-neutral-900 dark:border-white"
                      : "border border-neutral-300 dark:border-neutral-700"
                }`}
              >
                {done ? "✓" : ""}
              </span>
              <span
                className={
                  done || active
                    ? "text-neutral-800 dark:text-neutral-200"
                    : "text-neutral-400 dark:text-neutral-600"
                }
              >
                {t(`generationStages.${stage}`)}
              </span>
            </li>
          );
        })}
      </ul>

      <div className="mt-4">
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-neutral-100 dark:bg-neutral-800">
          <div
            className="h-full rounded-full bg-neutral-900 transition-all duration-500 dark:bg-white"
            style={{ width: `${generation.progress ?? 0}%` }}
          />
        </div>
        <p className="mt-1.5 text-xs text-neutral-400">
          {generation.progress ?? 0}%
        </p>
      </div>
    </div>
  );
}
