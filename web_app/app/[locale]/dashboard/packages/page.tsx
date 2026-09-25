"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { usePackage } from "@/lib/package/package-context";
import { Button } from "@/components/ui/Button";
import { useRouter } from "@/i18n/navigation";

const PLANS = [
  { id: "starter", name: "Starter", videos: 5, price: "৳990/mo" },
  { id: "growth", name: "Growth", videos: 15, price: "৳2,490/mo" },
  { id: "business", name: "Business", videos: 40, price: "৳5,990/mo" },
];

function PackagesContent() {
  const t = useTranslations("dashboard");
  const { pkg } = usePackage();
  const router = useRouter();
  const searchParams = useSearchParams();
  const returnConversation = searchParams.get("return");

  function handleMockPurchase() {
    // MOCK: in production this hits the real billing endpoint, then
    // navigates back. We only need to prove the "don't lose the
    // conversation while buying a package" requirement here.
    if (returnConversation) {
      router.push(`/dashboard/create?c=${returnConversation}&purchased=1`);
    }
  }

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8 md:px-8">
      <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
        {t("packageTitle")}
      </h1>
      {pkg && (
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          {t("nav.packages")}: {pkg.planName} · {t("videosRemaining", { count: pkg.videosRemaining })}
        </p>
      )}

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        {PLANS.map((plan) => (
          <div
            key={plan.id}
            className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm dark:border-neutral-800 dark:bg-neutral-900"
          >
            <h2 className="text-base font-semibold text-neutral-900 dark:text-neutral-100">
              {plan.name}
            </h2>
            <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
              {plan.videos} videos / month
            </p>
            <p className="mt-3 text-lg font-semibold text-neutral-900 dark:text-neutral-100">
              {plan.price}
            </p>
            <Button size="sm" className="mt-4 w-full" onClick={handleMockPurchase}>
              {returnConversation ? "Buy & return to chat" : "Choose plan"}
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function PackagesPage() {
  return (
    <Suspense fallback={null}>
      <PackagesContent />
    </Suspense>
  );
}
