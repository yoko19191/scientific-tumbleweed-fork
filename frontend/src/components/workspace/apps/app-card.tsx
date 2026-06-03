"use client";

import {
  ArrowRightIcon,
  BarChart3Icon,
  BookOpenTextIcon,
  DnaIcon,
  FileTextIcon,
  FlaskConicalIcon,
  LayoutGridIcon,
  SearchIcon,
  SparklesIcon,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { WorkspaceApp } from "@/core/apps";
import { useI18n } from "@/core/i18n/hooks";
import { cn } from "@/lib/utils";

const APP_ICONS: Record<string, LucideIcon> = {
  "bar-chart": BarChart3Icon,
  book: BookOpenTextIcon,
  dna: DnaIcon,
  file: FileTextIcon,
  flask: FlaskConicalIcon,
  "layout-grid": LayoutGridIcon,
  search: SearchIcon,
};

const CATEGORY_ACCENTS: Record<string, string> = {
  analysis:
    "bg-emerald-500/10 text-emerald-700 ring-emerald-500/20 dark:text-emerald-300 dark:ring-emerald-400/20",
  literature:
    "bg-sky-500/10 text-sky-700 ring-sky-500/20 dark:text-sky-300 dark:ring-sky-400/20",
  writing:
    "bg-amber-500/10 text-amber-700 ring-amber-500/20 dark:text-amber-300 dark:ring-amber-400/20",
};

export function AppCard({ app }: { app: WorkspaceApp }) {
  const { t } = useI18n();
  const Icon = APP_ICONS[app.icon] ?? LayoutGridIcon;
  const launch = app.status === "available" ? app.launch : null;
  const canLaunch = Boolean(launch);
  const accent =
    CATEGORY_ACCENTS[app.category] ??
    "bg-muted text-muted-foreground ring-border";

  return (
    <article className="group bg-card hover:border-primary/30 flex min-h-64 flex-col justify-between rounded-lg border p-5 shadow-sm transition-[border-color,box-shadow,transform] hover:-translate-y-0.5 hover:shadow-md">
      <div className="space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div
            className={cn(
              "flex size-11 shrink-0 items-center justify-center rounded-lg ring-1",
              accent,
            )}
          >
            <Icon className="size-5" />
          </div>
          <div className="flex flex-wrap justify-end gap-1.5">
            {app.featured && (
              <Badge variant="secondary">
                <SparklesIcon />
                {t.apps.featured}
              </Badge>
            )}
            {app.status === "coming_soon" && (
              <Badge variant="outline">{t.apps.comingSoon}</Badge>
            )}
          </div>
        </div>
        <div className="space-y-2">
          <div className="text-muted-foreground text-xs font-medium">
            {formatCategory(app.category)}
          </div>
          <h2 className="text-base font-semibold">{app.title}</h2>
          <p className="text-muted-foreground line-clamp-3 text-sm leading-6">
            {app.description}
          </p>
        </div>
      </div>
      <div className="mt-5 flex items-center justify-between gap-3 border-t pt-4">
        <span className="text-muted-foreground min-w-0 truncate text-xs">
          {app.meta || app.tags.join(" / ")}
        </span>
        <Button
          size="sm"
          variant={canLaunch ? "default" : "outline"}
          disabled={!canLaunch}
          asChild={Boolean(canLaunch)}
        >
          {launch ? (
            <Link href={launch.href}>
              {t.apps.openApp}
              <ArrowRightIcon className="size-4" />
            </Link>
          ) : (
            <span>{t.apps.openApp}</span>
          )}
        </Button>
      </div>
    </article>
  );
}

export function formatCategory(category: string) {
  return category
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((part) => part[0]?.toUpperCase() + part.slice(1))
    .join(" ");
}
