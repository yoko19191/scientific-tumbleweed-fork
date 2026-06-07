"use client";

import { DnaIcon, GlobeIcon, MenuIcon, XIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
    <header className="sticky top-3 z-50 px-3 sm:px-4">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between rounded-[10px] border border-[var(--lab-border-soft)]/70 bg-[var(--lab-bg-main)]/72 px-4 shadow-[0_18px_50px_rgb(38_55_41/0.12)] backdrop-blur-2xl sm:px-6 lg:px-8">
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
          <LanguageMenu locale={locale} onChange={setLanguage} />
          <Button asChild className="bg-[var(--lab-accent)] text-white shadow-[0_7px_0_var(--lab-accent-deep),0_18px_30px_hsla(24,92%,48%,0.22)] hover:-translate-y-0.5 hover:bg-[var(--lab-accent-hover)]">
            <Link href="/workspace">{t.marketing.nav.workbench}</Link>
          </Button>
        </div>

        <div className="flex items-center gap-3 lg:hidden">
          <Button asChild size="sm" className="bg-[var(--lab-accent)] text-white">
            <Link href="/workspace">{t.marketing.nav.workbench}</Link>
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
        <div className="mx-auto mt-2 max-w-7xl rounded-[10px] border border-[var(--lab-border-soft)]/70 bg-[var(--lab-surface)]/88 px-4 py-4 shadow-[0_18px_50px_rgb(38_55_41/0.12)] backdrop-blur-2xl lg:hidden">
          <div className="mb-4 flex items-center justify-between">
            <span className="font-mono text-xs uppercase tracking-[0.18em] text-[var(--lab-text-muted)]">
              LANG
            </span>
            <LanguageMenu locale={locale} onChange={setLanguage} />
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

function LanguageMenu({
  locale,
  onChange,
}: {
  locale: Locale;
  onChange: (locale: Locale) => void;
}) {
  const handleValueChange = (value: string) => {
    if (value === "en-US" || value === "zh-CN") {
      onChange(value);
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          aria-label="Select language"
          className="grid size-9 place-items-center rounded-[6px] bg-transparent text-[var(--lab-text-sub)] transition-colors hover:bg-[var(--lab-surface)]/58 hover:text-[var(--lab-primary)]"
        >
          <GlobeIcon className="size-5" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        className="border-[var(--lab-border-soft)] bg-[var(--lab-surface)]/94 text-[var(--lab-text-main)] shadow-[0_18px_44px_rgb(38_55_41/0.14)] backdrop-blur-xl"
      >
        <DropdownMenuRadioGroup value={locale} onValueChange={handleValueChange}>
          <DropdownMenuRadioItem value="en-US" className={cn(locale === "en-US" && "text-[var(--lab-primary)]")}>
            English
          </DropdownMenuRadioItem>
          <DropdownMenuRadioItem value="zh-CN" className={cn(locale === "zh-CN" && "text-[var(--lab-primary)]")}>
            中文
          </DropdownMenuRadioItem>
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
