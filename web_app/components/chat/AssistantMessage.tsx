import type { ReactNode } from "react";
import { SparklesIcon } from "@/components/ui/icons";

export function AssistantMessage({
  children,
  bare = false,
}: {
  children: ReactNode;
  /** true for rich cards, which render their own surface/border. */
  bare?: boolean;
}) {
  return (
    <div className="flex items-start gap-2.5">
      <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-white">
        <SparklesIcon className="h-3.5 w-3.5" />
      </div>
      {bare ? (
        <div className="min-w-0 flex-1">{children}</div>
      ) : (
        <div className="max-w-[85%] rounded-2xl rounded-tl-sm border border-neutral-200 bg-white px-4 py-2.5 text-sm text-neutral-800 dark:border-neutral-800 dark:bg-neutral-900 dark:text-neutral-100">
          {children}
        </div>
      )}
    </div>
  );
}
