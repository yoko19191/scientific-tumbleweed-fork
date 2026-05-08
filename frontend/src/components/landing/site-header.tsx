"use client";

import { ArrowRightIcon, DnaIcon, MenuIcon, XIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { useI18n } from "@/core/i18n/hooks";
import type { Locale } from "@/core/i18n/locale";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { href: "/product", key: "product" },
  { href: "/use-case", key: "useCase" },
  { href: "/research", key: "research" },
  { href: "/blog", key: "blog" },
  { href: "/pricing", key: "pricing" },
  { href: "/about", key: "about" },
] as const;

export function SiteHeader() {
  const pathname = usePathname();
  const { changeLocale, locale, t } = useI18n();
  const [open, setOpen] = useState(false);

  const setLanguage = (nextLocale: Locale) => {
    changeLocale(nextLocale);
    setOpen(false);
  };

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--lab-border-soft)]/80 bg-[var(--lab-bg-main)]/88 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link
          href="/"
          className="group flex items-center gap-3"
          aria-label="Scientific Tumbleweed home"
        >
          <span className="grid size-9 place-items-center rounded-md border border-[var(--lab-primary)]/25 bg-[var(--lab-surface)] text-[var(--lab-primary)] shadow-[0_2px_0_hsla(225,76%,52%,0.18)]">
            <DnaIcon className="size-5" />
          </span>
          <span className="font-serif text-lg font-semibold tracking-tight text-[var(--lab-text-main)]">
            Scientific Tumbleweed
          </span>
        </Link>

        <nav className="hidden items-center gap-7 text-sm font-medium text-[var(--lab-text-sub)] lg:flex">
          {NAV_LINKS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "transition-colors hover:text-[var(--lab-primary)]",
                pathname === item.href && "text-[var(--lab-primary)]",
              )}
            >
              {t.marketing.nav[item.key]}
            </Link>
          ))}
        </nav>

        <div className="hidden items-center gap-4 lg:flex">
          <LanguageSwitch locale={locale} onChange={setLanguage} />
          <Button asChild className="bg-[var(--lab-accent)] text-white shadow-[0_7px_0_var(--lab-accent-deep),0_18px_30px_hsla(24,92%,48%,0.22)] hover:-translate-y-0.5 hover:bg-[var(--lab-accent-hover)]">
            <Link href="/workspace">
              {t.marketing.nav.tryNow}
              <ArrowRightIcon className="size-4" />
            </Link>
          </Button>
        </div>

        <div className="flex items-center gap-3 lg:hidden">
          <Button asChild size="sm" className="bg-[var(--lab-accent)] text-white">
            <Link href="/workspace">{t.marketing.nav.tryNow}</Link>
          </Button>
          <button
            type="button"
            aria-label="Toggle navigation"
            className="grid size-10 place-items-center rounded-md border border-[var(--lab-border-soft)] bg-[var(--lab-surface)]"
            onClick={() => setOpen((value) => !value)}
          >
            {open ? <XIcon className="size-5" /> : <MenuIcon className="size-5" />}
          </button>
        </div>
      </div>

      {open ? (
        <div className="border-t border-[var(--lab-border-soft)] bg-[var(--lab-surface)] px-4 py-4 lg:hidden">
          <div className="mb-4 flex items-center justify-between">
            <span className="font-mono text-xs uppercase tracking-[0.18em] text-[var(--lab-text-muted)]">
              Language
            </span>
            <LanguageSwitch locale={locale} onChange={setLanguage} />
          </div>
          <nav className="grid gap-2">
            {NAV_LINKS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-md px-3 py-3 text-sm font-medium text-[var(--lab-text-main)] hover:bg-[var(--lab-surface-strong)]"
                onClick={() => setOpen(false)}
              >
                {t.marketing.nav[item.key]}
              </Link>
            ))}
          </nav>
        </div>
      ) : null}
    </header>
  );
}

function LanguageSwitch({
  locale,
  onChange,
}: {
  locale: Locale;
  onChange: (locale: Locale) => void;
}) {
  return (
    <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-[0.14em] text-[var(--lab-text-muted)]">
      <button
        type="button"
        className={cn(
          "transition-colors hover:text-[var(--lab-primary)]",
          locale === "en-US" && "text-[var(--lab-primary)]",
        )}
        onClick={() => onChange("en-US")}
      >
        EN
      </button>
      <span className="text-[var(--lab-divider)]">·</span>
      <button
        type="button"
        className={cn(
          "transition-colors hover:text-[var(--lab-primary)]",
          locale === "zh-CN" && "text-[var(--lab-primary)]",
        )}
        onClick={() => onChange("zh-CN")}
      >
        中
      </button>
    </div>
  );
}
