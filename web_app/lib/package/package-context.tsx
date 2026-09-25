"use client";

/**
 * MOCK PACKAGE / QUOTA STATE — isolated local implementation.
 *
 * Stands in for the real billing/quota service. Backed by localStorage so
 * the "package check" and "consume quota on generate" steps in the chat
 * workflow behave consistently across a demo session. Replace with a real
 * `GET /api/billing/package` + server-enforced quota decrement later; the
 * `usePackage()` contract is designed to map onto that directly.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type PackageInfo = {
  planName: string;
  videosRemaining: number;
  videosTotal: number;
};

type PackageContextValue = {
  pkg: PackageInfo | null;
  isLoading: boolean;
  hasQuota: boolean;
  consumeCredit: () => void;
  refundCredit: () => void;
};

const PackageContext = createContext<PackageContextValue | null>(null);

const STORAGE_KEY = "blinkora.mockPackage.state";

const DEFAULT_PACKAGE: PackageInfo = {
  planName: "Starter",
  videosRemaining: 4,
  videosTotal: 5,
};

function readStoredPackage(): PackageInfo {
  if (typeof window === "undefined") return DEFAULT_PACKAGE;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as PackageInfo) : DEFAULT_PACKAGE;
  } catch {
    return DEFAULT_PACKAGE;
  }
}

export function PackageProvider({ children }: { children: ReactNode }) {
  const [pkg, setPkg] = useState<PackageInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // See the matching comment in auth-context.tsx: deferred to an effect
    // on purpose to keep the first client render hydration-safe.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPkg(readStoredPackage());
    setIsLoading(false);
  }, []);

  const persist = useCallback((next: PackageInfo) => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    setPkg(next);
  }, []);

  const consumeCredit = useCallback(() => {
    setPkg((current) => {
      const base = current ?? DEFAULT_PACKAGE;
      const next = {
        ...base,
        videosRemaining: Math.max(0, base.videosRemaining - 1),
      };
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  const refundCredit = useCallback(() => {
    setPkg((current) => {
      const base = current ?? DEFAULT_PACKAGE;
      const next = {
        ...base,
        videosRemaining: Math.min(base.videosTotal, base.videosRemaining + 1),
      };
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  const value = useMemo(
    () => ({
      pkg,
      isLoading,
      hasQuota: (pkg?.videosRemaining ?? 0) > 0,
      consumeCredit,
      refundCredit,
    }),
    [pkg, isLoading, consumeCredit, refundCredit],
  );

  // `persist` kept referenced so future real-API swap can call it directly.
  void persist;

  return (
    <PackageContext.Provider value={value}>{children}</PackageContext.Provider>
  );
}

export function usePackage() {
  const ctx = useContext(PackageContext);
  if (!ctx) throw new Error("usePackage must be used within PackageProvider");
  return ctx;
}
