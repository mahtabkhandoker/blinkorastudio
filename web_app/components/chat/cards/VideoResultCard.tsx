"use client";

import { useTranslations } from "next-intl";
import type { CreativeInput, GenerationState } from "@/lib/chat/types";
import { Button } from "@/components/ui/Button";
import { DownloadIcon, RefreshIcon } from "@/components/ui/icons";

export function VideoResultCard({
  generation,
  input,
  onFollowUp,
  onRegenerate,
  onMakeChanges,
}: {
  generation: GenerationState;
  input: CreativeInput;
  onFollowUp: (label: string, patch?: Partial<CreativeInput>) => void;
  onRegenerate: () => void;
  onMakeChanges: () => void;
}) {
  const t = useTranslations("chat");

  const followUps: { label: string; patch?: Partial<CreativeInput> }[] = [
    { label: t("result.followUps.morePremium"), patch: { style: ["premium"] } },
    { label: t("result.followUps.changeMusic") },
    {
      label: t("result.followUps.shorter"),
      patch: input.duration ? { duration: Math.max(10, input.duration - 5) } : undefined,
    },
    { label: t("result.followUps.anotherImage") },
    { label: t("result.followUps.addCaptions"), patch: { captions: true } },
  ];

  return (
    <div className="w-full max-w-lg rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
      {generation.versionLabel && (
        <p className="mb-2 text-xs font-medium text-indigo-600">{generation.versionLabel}</p>
      )}
      <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
        {t("result.readyTitle")}
      </h3>

      <div className="mt-3 overflow-hidden rounded-xl bg-black">
        {generation.videoUrl && (
          <video
            src={generation.videoUrl}
            controls
            className="aspect-[9/16] w-full max-h-[420px] bg-black"
            aria-label="Generated marketing video preview"
          />
        )}
      </div>

      <p className="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
        {input.duration ?? 15} sec · {input.aspectRatio ?? "9:16"} ·{" "}
        {input.style?.map((s) => t(`quickReplies.${s}`)).join(" · ") || "Custom"}{" "}
        {input.campaignType ?? ""}
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        <a href={generation.videoUrl} download className="inline-flex">
          <Button size="sm" variant="secondary">
            <DownloadIcon className="h-4 w-4" />
            {t("download")}
          </Button>
        </a>
        <Button size="sm" variant="secondary" onClick={onRegenerate}>
          <RefreshIcon className="h-4 w-4" />
          {t("regenerate")}
        </Button>
        <Button size="sm" variant="ghost" onClick={onMakeChanges}>
          {t("makeChanges")}
        </Button>
      </div>

      <div className="mt-4 flex flex-wrap gap-1.5">
        {followUps.map((f) => (
          <button
            key={f.label}
            type="button"
            onClick={() => onFollowUp(f.label, f.patch)}
            className="rounded-full border border-neutral-200 px-3 py-1.5 text-xs text-neutral-600 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
          >
            {f.label}
          </button>
        ))}
      </div>
    </div>
  );
}
