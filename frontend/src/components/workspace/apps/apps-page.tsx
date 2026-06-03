"use client";

import { LayoutGridIcon, SearchIcon } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { useApps } from "@/core/apps";
import { useI18n } from "@/core/i18n/hooks";
import { cn } from "@/lib/utils";

import { AppCard, formatCategory } from "./app-card";
import { AppsEmptyState } from "./apps-empty-state";

const ALL_CATEGORY = "__all__";

export function AppsPage() {
  const { t } = useI18n();
  const { apps, isLoading, error } = useApps();
  const [activeCategory, setActiveCategory] = useState(ALL_CATEGORY);
  const [search, setSearch] = useState("");

  useEffect(() => {
    document.title = `${t.apps.title} - ${t.pages.appName}`;
  }, [t.apps.title, t.pages.appName]);

  const categories = useMemo(
    () => Array.from(new Set(apps.map((app) => app.category))).sort(),
    [apps],
  );

  const visibleApps = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return apps.filter((app) => {
      const matchesCategory =
        activeCategory === ALL_CATEGORY || app.category === activeCategory;
      const matchesSearch =
        normalizedSearch.length === 0 ||
        app.title.toLowerCase().includes(normalizedSearch) ||
        app.description.toLowerCase().includes(normalizedSearch) ||
        app.category.toLowerCase().includes(normalizedSearch) ||
        app.meta.toLowerCase().includes(normalizedSearch) ||
        app.tags.some((tag) => tag.toLowerCase().includes(normalizedSearch));
      return matchesCategory && matchesSearch;
    });
  }, [activeCategory, apps, search]);

  const isFiltered =
    apps.length > 0 &&
    (search.trim().length > 0 || activeCategory !== ALL_CATEGORY);

  return (
    <div className="flex size-full flex-col">
      <div className="border-b px-6 py-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="mb-2 flex items-center gap-2">
              <div className="bg-primary/10 text-primary flex size-8 shrink-0 items-center justify-center rounded-lg">
                <LayoutGridIcon className="size-4" />
              </div>
              <h1 className="text-xl font-semibold">{t.apps.title}</h1>
            </div>
            <p className="text-muted-foreground max-w-2xl text-sm">
              {t.apps.description}
            </p>
          </div>
          <div className="grid min-w-64 grid-cols-3 overflow-hidden rounded-lg border">
            <AppStat value={apps.length} label={t.apps.stats.registered} />
            <AppStat
              value={categories.length}
              label={t.apps.stats.categories}
            />
            <AppStat
              value={apps.filter((app) => app.featured).length}
              label={t.apps.stats.featured}
            />
          </div>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col">
        {apps.length > 0 && (
          <div className="flex flex-wrap items-center gap-3 border-b px-6 py-3">
            <div className="relative min-w-56 flex-1 sm:max-w-sm">
              <SearchIcon className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2" />
              <Input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder={t.apps.searchPlaceholder}
                className="h-9 pl-9"
              />
            </div>
            <div
              className="bg-muted flex flex-wrap gap-1 rounded-lg p-1"
              aria-label={t.apps.categoryFilterLabel}
            >
              {[ALL_CATEGORY, ...categories].map((category) => (
                <button
                  key={category}
                  type="button"
                  onClick={() => setActiveCategory(category)}
                  className={cn(
                    "h-7 rounded-md px-3 text-xs font-medium transition-colors",
                    activeCategory === category
                      ? "bg-background text-foreground shadow-xs"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {category === ALL_CATEGORY
                    ? t.apps.allCategories
                    : formatCategory(category)}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="min-h-0 flex-1 overflow-y-auto p-6">
          {isLoading ? (
            <div className="text-muted-foreground flex h-40 items-center justify-center text-sm">
              {t.common.loading}
            </div>
          ) : error ? (
            <Alert variant="destructive" className="max-w-3xl">
              <AlertTitle>{t.apps.errorTitle}</AlertTitle>
              <AlertDescription>{t.apps.errorDescription}</AlertDescription>
            </Alert>
          ) : visibleApps.length > 0 ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {visibleApps.map((app) => (
                <AppCard key={app.id} app={app} />
              ))}
            </div>
          ) : (
            <AppsEmptyState isFiltered={isFiltered} />
          )}
        </div>
      </div>
    </div>
  );
}

function AppStat({ value, label }: { value: string | number; label: string }) {
  return (
    <div className="flex min-w-0 flex-col items-center justify-center border-r px-4 py-3 last:border-r-0">
      <div className="text-sm font-semibold tabular-nums">{value}</div>
      <div className="text-muted-foreground mt-0.5 truncate text-xs">
        {label}
      </div>
    </div>
  );
}
