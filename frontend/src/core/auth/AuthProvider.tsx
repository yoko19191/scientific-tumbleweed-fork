"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";

import { queryClient } from "@/components/query-client-provider";

import {
  fetchCurrentUser,
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
} from "./fetcher";
import type {
  AuthState,
  LoginCredentials,
  RegisterCredentials,
  User,
} from "./types";

interface AuthContextValue extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (credentials: RegisterCredentials) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/** Clear all TanStack Query caches and lg:stream sessionStorage keys. */
function clearAllCaches(userId?: string | null): void {
  queryClient.clear();
  if (typeof window !== "undefined") {
    // Remove all lg:stream:* keys (both scoped and unscoped)
    const keysToRemove: string[] = [];
    for (let i = 0; i < window.sessionStorage.length; i++) {
      const k = window.sessionStorage.key(i);
      if (k && (k.startsWith("lg:stream:") || k.includes(":lg:stream:"))) {
        keysToRemove.push(k);
      }
    }
    keysToRemove.forEach((k) => window.sessionStorage.removeItem(k));
    void userId; // userId param reserved for future per-user scoped clearing
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  // Track previous user ID to detect user switches
  const prevUserIdRef = useRef<string | null>(null);

  const refreshUser = useCallback(async () => {
    try {
      const u = await fetchCurrentUser();
      setUser(u);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // Clear caches when the authenticated user changes (switch accounts)
  useEffect(() => {
    const currentId = user?.id ?? null;
    if (prevUserIdRef.current !== null && prevUserIdRef.current !== currentId) {
      // User switched — clear all cached data so the new user sees a clean slate
      clearAllCaches(prevUserIdRef.current);
    }
    prevUserIdRef.current = currentId;
  }, [user]);

  // Check session on mount
  useEffect(() => {
    void refreshUser();
  }, [refreshUser]);

  // Re-check session when tab becomes visible
  useEffect(() => {
    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        void refreshUser();
      }
    };
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () =>
      document.removeEventListener("visibilitychange", onVisibilityChange);
  }, [refreshUser]);

  const login = useCallback(
    async (credentials: LoginCredentials) => {
      await apiLogin(credentials);
      await refreshUser();
    },
    [refreshUser],
  );

  const register = useCallback(
    async (credentials: RegisterCredentials) => {
      await apiRegister(credentials);
      await refreshUser();
    },
    [refreshUser],
  );

  const logout = useCallback(async () => {
    const loggedOutUserId = user?.id ?? null;
    await apiLogout();
    // Clear all cached data so the next user sees a clean slate
    clearAllCaches(loggedOutUserId);
    setUser(null);
  }, [user]);

  const value = useMemo<AuthContextValue>(
    () => ({ user, loading, login, register, logout, refreshUser }),
    [user, loading, login, register, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
