"use client";

/**
 * MOCK AUTH — isolated local implementation.
 *
 * There is no real backend/auth service wired up yet. This provider fakes a
 * signed-in session with localStorage so the dashboard/chat UI can be built
 * and demoed end-to-end. Replace this file's internals with real session
 * handling (e.g. cookies/JWT from the FastAPI backend) without touching the
 * consumer components — they only depend on the `useAuth()` contract below.
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

export type MockUser = {
  id: string;
  name: string;
  email: string;
};

type AuthContextValue = {
  user: MockUser | null;
  isLoading: boolean;
  login: (email: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const STORAGE_KEY = "blinkora.mockAuth.user";

function readStoredUser(): MockUser | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as MockUser) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<MockUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Intentionally deferred to an effect (not a lazy useState initializer)
    // so the very first client render matches the server-rendered markup
    // (which has no access to localStorage) before hydrating in the mock
    // session. This is the standard hydration-safe pattern.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setUser(readStoredUser());
    setIsLoading(false);
  }, []);

  const login = useCallback(async (email: string) => {
    // Simulated network latency; swap for a real POST /api/auth/login call.
    await new Promise((resolve) => setTimeout(resolve, 500));
    const name = email.split("@")[0] || "Business Owner";
    const nextUser: MockUser = {
      id: `mock-${email}`,
      name: name.charAt(0).toUpperCase() + name.slice(1),
      email,
    };
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(nextUser));
    setUser(nextUser);
  }, []);

  const logout = useCallback(() => {
    window.localStorage.removeItem(STORAGE_KEY);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, isLoading, login, logout }),
    [user, isLoading, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
