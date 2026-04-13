"use client";

import { LogOutIcon } from "lucide-react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/core/auth/AuthProvider";
import { useI18n } from "@/core/i18n/hooks";

export function AccountSettingsPage({ onClose }: { onClose?: () => void } = {}) {
  const { t } = useI18n();
  const { user, logout } = useAuth();
  const router = useRouter();

  const handleLogout = async () => {
    onClose?.();
    await logout();
    router.push("/login");
  };

  if (!user) return null;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">{t.account.title}</h2>
      </div>

      <div className="space-y-4">
        <div className="space-y-1">
          <p className="text-sm font-medium text-muted-foreground">{t.account.displayName}</p>
          <p className="text-sm">{user.display_name || "—"}</p>
        </div>

        <div className="space-y-1">
          <p className="text-sm font-medium text-muted-foreground">{t.account.username}</p>
          <p className="text-sm font-mono">@{user.username || "—"}</p>
        </div>

        <div className="space-y-1">
          <p className="text-sm font-medium text-muted-foreground">{t.account.email}</p>
          <p className="text-sm">{user.email}</p>
        </div>
      </div>

      <div className="border-t border-border pt-4">
        <button
          type="button"
          onClick={handleLogout}
          className="flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-destructive hover:bg-destructive/10 transition-colors"
        >
          <LogOutIcon className="size-4" />
          {t.account.logout}
        </button>
      </div>
    </div>
  );
}
