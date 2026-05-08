"use client";

import { ArrowRightIcon, BellIcon } from "lucide-react";
import Link from "next/link";

import { SiteFooter } from "@/components/landing/site-footer";
import { SiteHeader } from "@/components/landing/site-header";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/core/i18n/hooks";

type MarketingPageKey = "about" | "blog" | "pricing" | "product" | "research" | "useCase";

export function MarketingPageShell({ pageKey }: { pageKey: MarketingPageKey }) {
  const { t } = useI18n();
  const page = t.marketing.pages[pageKey];
  const showSubscribe = pageKey === "blog" || pageKey === "research";
  const showPricingActions = pageKey === "pricing";

  return (
    <div className="min-h-screen bg-[var(--lab-bg-main)] text-[var(--lab-text-main)]">
      <SiteHeader />
      <main>
        <section className="relative overflow-hidden border-b border-[var(--lab-border-soft)] px-4 py-24 sm:px-6 lg:px-8">
          <div className="absolute inset-0 -z-10 bg-[url('/landing/biomed-cta.png')] bg-cover bg-center opacity-70" />
          <div className="absolute inset-0 -z-10 bg-[var(--lab-bg-main)]/78" />
          <div className="mx-auto max-w-5xl">
            {page.eyebrow ? (
              <p className="mb-5 font-mono text-xs uppercase tracking-[0.22em] text-[var(--lab-primary)]">
                {page.eyebrow}
              </p>
            ) : null}
            <h1 className="max-w-4xl font-serif text-5xl font-semibold leading-[1.02] tracking-tight text-[var(--lab-text-main)] sm:text-6xl lg:text-7xl">
              {page.headline}
            </h1>
            <p className="mt-7 max-w-2xl text-lg leading-8 text-[var(--lab-text-sub)]">
              {page.subhead}
            </p>

            {showSubscribe ? (
              <form className="mt-10 flex max-w-lg flex-col gap-3 sm:flex-row">
                <input
                  type="email"
                  placeholder="your@email.com"
                  className="h-12 min-w-0 flex-1 rounded-md border border-[var(--lab-border)] bg-[var(--lab-surface)] px-4 text-sm outline-none focus:border-[var(--lab-primary)]"
                />
                <Button type="button" className="h-12 bg-[var(--lab-primary)] text-white hover:bg-[var(--lab-primary-hover)]">
                  <BellIcon className="size-4" />
                  {"subscribe" in page ? page.subscribe : "Notify me"}
                </Button>
              </form>
            ) : null}
          </div>
        </section>

        <section className="px-4 py-20 sm:px-6 lg:px-8">
          <div className="mx-auto grid max-w-6xl gap-5 md:grid-cols-2 lg:grid-cols-3">
            {page.cards.map((card) => (
              <article
                key={card.title}
                className="min-h-52 rounded-lg border border-[var(--lab-border-soft)] bg-[var(--lab-surface)] p-6 shadow-[0_8px_28px_hsla(210,30%,20%,0.06)]"
              >
                {card.meta ? (
                  <p className="mb-4 font-mono text-xs uppercase tracking-[0.16em] text-[var(--lab-accent)]">
                    {card.meta}
                  </p>
                ) : null}
                <h2 className="font-serif text-2xl font-semibold leading-tight text-[var(--lab-text-main)]">
                  {card.title}
                </h2>
                {card.body ? (
                  <p className="mt-4 text-sm leading-7 text-[var(--lab-text-sub)]">{card.body}</p>
                ) : null}
                {showPricingActions ? (
                  <Button asChild className="mt-7 bg-[var(--lab-accent)] text-white hover:bg-[var(--lab-accent-hover)]">
                    <Link href="/about">
                      {t.marketing.nav.talkToUs}
                      <ArrowRightIcon className="size-4" />
                    </Link>
                  </Button>
                ) : null}
              </article>
            ))}
          </div>

          {pageKey === "research" && "footer" in page ? (
            <p className="mx-auto mt-12 max-w-3xl text-center text-sm leading-7 text-[var(--lab-text-muted)]">
              {page.footer}
            </p>
          ) : null}
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
