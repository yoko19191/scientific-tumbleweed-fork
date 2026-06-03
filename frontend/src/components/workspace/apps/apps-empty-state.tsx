"use client";

import { LayoutGridIcon } from "lucide-react";

import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { useI18n } from "@/core/i18n/hooks";

export function AppsEmptyState({
  isFiltered = false,
}: {
  isFiltered?: boolean;
}) {
  const { t } = useI18n();
  return (
    <Empty className="h-64 border">
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <LayoutGridIcon />
        </EmptyMedia>
        <EmptyTitle>
          {isFiltered ? t.apps.noResultsTitle : t.apps.emptyTitle}
        </EmptyTitle>
        <EmptyDescription>
          {isFiltered ? t.apps.noResultsDescription : t.apps.emptyDescription}
        </EmptyDescription>
      </EmptyHeader>
    </Empty>
  );
}
