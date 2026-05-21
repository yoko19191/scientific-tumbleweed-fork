"use client";

import { ContainerIcon } from "lucide-react";

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useSandboxCapacity } from "@/core/sandbox";
import { cn } from "@/lib/utils";

function getCapacityTone(usedPercent: number) {
  if (usedPercent > 85) {
    return {
      icon: "text-red-600",
      shell: "border-red-200/90 bg-red-50/95 shadow-[0_12px_26px_rgba(239,68,68,0.22)]",
      ring: "ring-red-200/80",
    };
  }
  if (usedPercent > 60) {
    return {
      icon: "text-amber-600",
      shell:
        "border-amber-200/90 bg-amber-50/95 shadow-[0_12px_26px_rgba(245,158,11,0.22)]",
      ring: "ring-amber-200/80",
    };
  }
  return {
    icon: "text-emerald-600",
    shell:
      "border-emerald-200/90 bg-emerald-50/95 shadow-[0_12px_26px_rgba(16,185,129,0.2)]",
    ring: "ring-emerald-200/80",
  };
}

export function SandboxCapacityIndicator({ className }: { className?: string }) {
  const { capacity, error } = useSandboxCapacity();

  if (error || !capacity?.enabled || capacity.limit === null) {
    return null;
  }

  const usedPercent =
    capacity.limit > 0
      ? Math.min(100, Math.max(0, (capacity.total / capacity.limit) * 100))
      : 0;
  const tone = getCapacityTone(usedPercent);
  const tooltipText = `沙盒环境可用容量： ${capacity.total}/${capacity.limit}`;

  return (
    <Tooltip delayDuration={100}>
      <TooltipTrigger asChild>
        <button
          type="button"
          aria-label={tooltipText}
          className={cn(
            "fixed bottom-8 left-[calc(var(--sidebar-width)+2rem)] z-[70] flex size-9 items-center justify-center rounded-xl border backdrop-blur-md",
            "transition-[left,border-color,background-color,box-shadow,transform] duration-200 hover:-translate-y-0.5 active:scale-95",
            "ring-1 group-has-data-[collapsible=icon]/sidebar-wrapper:left-[calc(var(--sidebar-width-icon)+2rem)]",
            tone.shell,
            tone.ring,
            className,
          )}
        >
          <ContainerIcon
            className={cn("size-4", tone.icon)}
            strokeWidth={2.2}
          />
        </button>
      </TooltipTrigger>
      <TooltipContent side="top" align="start" sideOffset={8}>
        {tooltipText}
      </TooltipContent>
    </Tooltip>
  );
}
