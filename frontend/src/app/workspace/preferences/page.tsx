"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { MemorySettingsPage } from "@/components/workspace/settings/memory-settings-page";
import { SkillSettingsPage } from "@/components/workspace/settings/skill-settings-page";
import { ToolSettingsPage } from "@/components/workspace/settings/tool-settings-page";
import { useI18n } from "@/core/i18n/hooks";
import { cn } from "@/lib/utils";

type PreferencesTab = "memory" | "tools" | "skills";

function PreferencesContent() {
  const { t } = useI18n();
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeTab = (searchParams.get("tab") as PreferencesTab) ?? "memory";

  const tabs: { id: PreferencesTab; label: string }[] = [
    { id: "memory", label: t.preferences.tabs.memory },
    { id: "tools", label: t.preferences.tabs.tools },
    { id: "skills", label: t.preferences.tabs.skills },
  ];

  const setTab = (tab: PreferencesTab) => {
    router.push(`/workspace/preferences?tab=${tab}`);
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-border px-6 py-4">
        <h1 className="text-xl font-semibold">{t.preferences.title}</h1>
      </div>

      {/* Horizontal tab nav */}
      <div className="border-b border-border px-6">
        <nav className="flex gap-1" aria-label="Preferences tabs">
          {tabs.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              onClick={() => setTab(id)}
              className={cn(
                "px-4 py-3 text-sm font-medium transition-colors border-b-2 -mb-px",
                activeTab === id
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground",
              )}
            >
              {label}
            </button>
          ))}
        </nav>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="max-w-3xl space-y-8">
          {activeTab === "memory" && <MemorySettingsPage />}
          {activeTab === "tools" && <ToolSettingsPage />}
          {activeTab === "skills" && <SkillSettingsPage />}
        </div>
      </div>
    </div>
  );
}

export default function PreferencesPage() {
  return (
    <Suspense>
      <PreferencesContent />
    </Suspense>
  );
}
