"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import type { CreativeInput } from "@/lib/chat/types";
import { Button } from "@/components/ui/Button";

const PLATFORM_LABEL: Record<NonNullable<CreativeInput["platform"]>, string> = {
  facebook_instagram: "Facebook / Instagram",
  tiktok_reels: "TikTok / Reels",
  youtube: "YouTube",
};

function buildVisualDirection(input: CreativeInput): string {
  const styleText = input.style?.join(", ") ?? "clean, modern";
  return `Natural product movement, ${styleText} lighting and camera motion, focus on product details and craftsmanship.`;
}

export function CreativeBriefCard({
  input,
  assetCount,
  confirmed,
  onEdit,
  onConfirm,
}: {
  input: CreativeInput;
  assetCount: number;
  confirmed: boolean;
  onEdit: () => void;
  onConfirm: () => void;
}) {
  const t = useTranslations("chat");
  const [showAdvanced, setShowAdvanced] = useState(false);

  const rows: { label: string; value?: string }[] = [
    { label: t("brief.product"), value: input.businessName ?? input.productCategory },
    { label: t("brief.campaign"), value: input.campaignType },
    { label: t("brief.duration"), value: input.duration ? `${input.duration} seconds` : undefined },
    { label: t("brief.format"), value: input.aspectRatio ? `${input.aspectRatio} Vertical/Square` : undefined },
    { label: t("brief.style"), value: input.style?.map((s) => t(`quickReplies.${s}`)).join(" · ") },
    { label: t("brief.audience"), value: input.targetAudience },
    { label: t("brief.assets"), value: assetCount ? `${assetCount} product photo${assetCount > 1 ? "s" : ""}` : undefined },
    { label: t("brief.captionLanguage"), value: input.captions === false ? undefined : input.language === "en" ? "English" : "Bangla" },
    { label: t("brief.cta"), value: input.cta ?? "আজই অর্ডার করুন" },
  ].filter((row) => row.value);

  return (
    <div className="w-full max-w-lg rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
      <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
        {t("brief.title")}
      </h3>

      <dl className="mt-3 space-y-2.5">
        {rows.map((row) => (
          <div key={row.label} className="flex justify-between gap-4 text-sm">
            <dt className="shrink-0 text-neutral-500 dark:text-neutral-400">{row.label}</dt>
            <dd className="text-right text-neutral-800 dark:text-neutral-200">{row.value}</dd>
          </div>
        ))}
        <div className="flex justify-between gap-4 text-sm">
          <dt className="shrink-0 text-neutral-500 dark:text-neutral-400">
            {t("brief.visualDirection")}
          </dt>
          <dd className="max-w-[70%] text-right text-neutral-800 dark:text-neutral-200">
            {buildVisualDirection(input)}
          </dd>
        </div>
        {input.platform && (
          <div className="flex justify-between gap-4 text-sm">
            <dt className="shrink-0 text-neutral-500 dark:text-neutral-400">Platform</dt>
            <dd className="text-right text-neutral-800 dark:text-neutral-200">
              {PLATFORM_LABEL[input.platform]}
            </dd>
          </div>
        )}
      </dl>

      <button
        type="button"
        onClick={() => setShowAdvanced((v) => !v)}
        className="mt-4 text-xs font-medium text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
        aria-expanded={showAdvanced}
      >
        {t("brief.advanced")} · {t("brief.viewPrompt")} {showAdvanced ? "▲" : "▼"}
      </button>

      {showAdvanced && (
        <pre className="mt-2 whitespace-pre-wrap rounded-lg bg-neutral-50 p-3 text-[11px] leading-relaxed text-neutral-500 dark:bg-neutral-950 dark:text-neutral-400">
          {`Scene: ${input.businessName ?? "product"} — ${input.campaignType ?? "promo"}\nDuration: ${input.duration ?? 15}s, ${input.aspectRatio ?? "9:16"}\nStyle: ${input.style?.join(", ") ?? "clean, modern"}\nCaptions: ${input.captions === false ? "off" : "on"} · Voiceover: ${input.voiceover === false ? "off" : "on"}\nCTA: ${input.cta ?? "আজই অর্ডার করুন"}`}
        </pre>
      )}

      {!confirmed && (
        <div className="mt-5 flex flex-wrap gap-2">
          <Button variant="secondary" size="sm" onClick={onEdit}>
            {t("editBrief")}
          </Button>
          <Button size="sm" onClick={onConfirm}>
            {t("confirmGenerate")}
          </Button>
        </div>
      )}
    </div>
  );
}
