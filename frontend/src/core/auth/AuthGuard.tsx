"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import type { ReactNode } from "react";

import { useI18n } from "../i18n/hooks";

import { useAuth } from "./AuthProvider";

/**
 * Redirects unauthenticated users to /login.
 * Shows nothing while the initial session check is in progress.
 */
export function AuthGuard({ children }: { children: ReactNode }) {
  const { t } = useI18n();
  const { user, loading, unavailable, refreshUser, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user && !unavailable) {
      router.replace("/login");
    }
  }, [loading, unavailable, user, router]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (unavailable && !user) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 px-6 text-center">
        <div className="text-sm font-medium">
          {t.sidebar.gatewayUnavailable}
        </div>
        <div className="text-muted-foreground max-w-md text-sm">
          {t.sidebar.gatewayUnavailableRetrying}
        </div>
        <div className="flex gap-3">
          <button
            type="button"
            className="bg-primary text-primary-foreground hover:bg-primary/90 rounded-md px-4 py-2 text-sm"
            onClick={() => void refreshUser()}
          >
            {t.common.retry}
          </button>
          <button
            type="button"
            className="text-muted-foreground hover:bg-muted rounded-md border px-4 py-2 text-sm"
            onClick={() => void logout()}
          >
            {t.account.logout}
          </button>
        </div>
      </div>
    );
  }

  if (!user) return null;

  return (
    <>
      {unavailable && (
        <div className="bg-background text-foreground fixed top-3 left-1/2 z-50 flex -translate-x-1/2 items-center gap-3 rounded-md border px-3 py-2 text-xs shadow-sm">
          <span>{t.sidebar.gatewayUnavailable}</span>
          <button
            type="button"
            className="underline underline-offset-2"
            onClick={() => void refreshUser()}
          >
            {t.common.retry}
          </button>
        </div>
      )}
      {children}
    </>
  );
}
