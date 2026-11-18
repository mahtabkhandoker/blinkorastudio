"use client";

/**
 * Real backend session auth: an httponly cookie (set by
 * `POST /api/auth/{register,login}`) is the only source of truth. This
 * provider never stores a token — on mount it asks the backend "who is
 * this cookie for" via `GET /api/auth/me`, which is also how a page
 * refresh restores the session. Logout calls the backend, which revokes
 * the session server-side; the local `user` is cleared either way.
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
import { AuthApiError, createAuthApi, type AuthUser } from "@/lib/api/auth";
import { getOrderApiUrl } from "@/lib/api/orders";

export type AuthUserView = {
  id: string;
  name: string;
  email: string;
};

type AuthContextValue = {
  user: AuthUserView | null;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const DEFAULT_API_URL = "http://localhost:8000";

function toView(user: AuthUser): AuthUserView {
  return { id: user.id, name: user.display_name, email: user.email };
}

function describe(caught: unknown): string {
  if (caught instanceof AuthApiError) {
    switch (caught.code) {
      case "INVALID_CREDENTIALS":
        return "Incorrect email or password.";
      case "EMAIL_TAKEN":
        return "An account with this email already exists.";
      case "RATE_LIMITED":
        return "Too many attempts. Please try again in a few minutes.";
      case "UNAVAILABLE":
        return "Could not reach the server. Check your connection and try again.";
    }
  }
  return "Something went wrong. Please try again.";
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const apiUrl = getOrderApiUrl() ?? DEFAULT_API_URL;
  const api = useMemo(() => createAuthApi(apiUrl), [apiUrl]);
  const [user, setUser] = useState<AuthUserView | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const me = await api.me();
        if (!cancelled) setUser(toView(me));
      } catch {
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [api]);

  const login = useCallback(
    async (email: string, password: string) => {
      setError(null);
      try {
        const loggedIn = await api.login(email, password);
        setUser(toView(loggedIn));
      } catch (caught) {
        setError(describe(caught));
        throw caught;
      }
    },
    [api],
  );

  const register = useCallback(
    async (email: string, password: string, displayName: string) => {
      setError(null);
      try {
        const created = await api.register(email, password, displayName);
        setUser(toView(created));
      } catch (caught) {
        setError(describe(caught));
        throw caught;
      }
    },
    [api],
  );

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // The cookie may already be gone (expired/revoked elsewhere); treat
      // local sign-out as unconditional either way.
    } finally {
      setUser(null);
    }
  }, [api]);

  const clearError = useCallback(() => setError(null), []);

  const value = useMemo(
    () => ({ user, isLoading, error, login, register, logout, clearError }),
    [user, isLoading, error, login, register, logout, clearError],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
