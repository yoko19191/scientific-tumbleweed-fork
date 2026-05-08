"use client";

import { useEffect, useState } from "react";

import { useI18n } from "@/core/i18n/hooks";
import { cn } from "@/lib/utils";

export function LandingToc() {
  const { t } = useI18n();
  const [active, setActive] = useState("hero");

  useEffect(() => {
    const sections = Array.from(
      document.querySelectorAll<HTMLElement>("[data-landing-section]"),
    );

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible?.target.id) {
          setActive(visible.target.id);
        }
      },
      {
        rootMargin: "-35% 0px -45% 0px",
        threshold: [0.05, 0.2, 0.45, 0.7],
      },
    );

    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, []);

  return (
    <nav
      aria-label="On this page"
      className="fixed right-6 top-1/2 z-40 hidden -translate-y-1/2 xl:block"
    >
      <ol className="space-y-1">
        {t.marketing.landing.toc.map((item, index) => {
          const id = item.href.replace("#", "");
          const isActive = active === id;
          const inLayerGroup = index >= 2 && index <= 4;

          return (
            <li key={item.href}>
              <a
                href={item.href}
                className={cn(
                  "group relative flex items-center gap-2 py-1.5 font-mono text-[11px] uppercase tracking-[0.14em] text-[var(--lab-text-muted)]/60 transition-all hover:translate-x-0.5 hover:text-[var(--lab-primary)]",
                  isActive && "font-semibold text-[var(--lab-primary)]",
                )}
              >
                {/* Hover tooltip */}
                <span className="pointer-events-none absolute right-full mr-3 top-1/2 z-50 -translate-y-1/2 whitespace-nowrap rounded-md border border-[var(--lab-border-soft)] bg-[var(--lab-surface)] px-3 py-1.5 text-xs font-medium text-[var(--lab-text-main)] opacity-0 shadow-[0_4px_12px_hsla(210,30%,20%,0.08)] transition-opacity group-hover:opacity-100">
                  {item.label}
                  {/* Arrow */}
                  <span className="absolute -right-1 top-1/2 size-2 -translate-y-1/2 rotate-45 border-r border-t border-[var(--lab-border-soft)] bg-[var(--lab-surface)]" />
                </span>

                <span
                  className={cn(
                    "h-5 rounded-full bg-[var(--lab-primary)]/20 transition-all",
                    isActive ? "w-1 bg-[var(--lab-primary)]" : "w-0.5",
                    inLayerGroup && !isActive && "bg-[var(--lab-accent)]/35",
                  )}
                />
                <span className="tabular-nums lg:hidden 2xl:inline">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span className={cn("max-w-36 truncate", !isActive && "hidden 2xl:inline")}>
                  {item.label}
                </span>
              </a>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
