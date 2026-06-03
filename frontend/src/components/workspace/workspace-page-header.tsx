"use client";

import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

export function WorkspacePageHeader({
  icon: Icon,
  title,
  description,
  actions,
  className,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("border-b px-6 py-4", className)}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="mb-2 flex items-center gap-2">
            <div className="bg-primary/10 text-primary flex size-8 shrink-0 items-center justify-center rounded-lg">
              <Icon className="size-4" />
            </div>
            <h1 className="text-xl font-semibold">{title}</h1>
          </div>
          <p className="text-muted-foreground max-w-2xl text-sm">
            {description}
          </p>
        </div>
        {actions}
      </div>
    </div>
  );
}
