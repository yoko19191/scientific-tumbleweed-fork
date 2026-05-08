"use client";

import { ArrowRightIcon, DnaIcon } from "lucide-react";
import Link from "next/link";

import { useI18n } from "@/core/i18n/hooks";

export function SiteFooter() {
  const { t } = useI18n();

  return (
    <footer className="border-t border-[var(--lab-border-soft)] bg-[var(--lab-ink-dark)] text-[var(--lab-on-dark)]">
      <div className="mx-auto grid max-w-7xl gap-12 px-4 py-14 sm:px-6 lg:grid-cols-[1.1fr_1fr] lg:px-8">
        <div className="space-y-6">
          <Link href="/" className="flex items-center gap-3">
            <span className="grid size-9 place-items-center rounded-md border border-white/15 bg-white/8">
              <DnaIcon className="size-5" />
            </span>
            <span className="font-serif text-xl font-semibold">
              Scientific Tumbleweed
            </span>
          </Link>
          <p className="max-w-md text-sm leading-7 text-[var(--lab-on-dark-muted)]">
            {t.marketing.footer.note}
          </p>
          <Link
            href="/workspace"
            className="inline-flex items-center gap-2 rounded-md bg-[var(--lab-accent)] px-4 py-3 text-sm font-semibold text-white shadow-[0_6px_0_var(--lab-accent-deep)] transition-transform hover:-translate-y-0.5"
          >
            {t.marketing.nav.tryNow}
            <ArrowRightIcon className="size-4" />
          </Link>
        </div>

        <div className="grid gap-8 sm:grid-cols-3">
          {t.marketing.footer.columns.map((column) => (
            <div key={column.title}>
              <h3 className="mb-4 font-mono text-xs uppercase tracking-[0.18em] text-[var(--lab-on-dark-muted)]">
                {column.title}
              </h3>
              <ul className="space-y-3 text-sm text-[var(--lab-on-dark)]/86">
                {column.links.map((link) => (
                  <li key={link}>{link}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
      <div className="border-t border-white/10 px-4 py-5 text-center font-mono text-[11px] uppercase tracking-[0.2em] text-white/45 sm:px-6 lg:px-8">
        © 2026 Scientific Tumbleweed
      </div>
    </footer>
  );
}
