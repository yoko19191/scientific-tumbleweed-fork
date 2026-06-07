"use client";

import { ArrowRightIcon, CheckCircle2Icon } from "lucide-react";
import Link from "next/link";
import { type ReactNode } from "react";

import { LandingToc } from "@/components/landing/landing-toc";
import { LandingScrollEffects } from "@/components/landing/scroll-effects";
import { SiteFooter } from "@/components/landing/site-footer";
import { SiteHeader } from "@/components/landing/site-header";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/core/i18n/hooks";
import { cn } from "@/lib/utils";

const DNA_PAIRS = [
  ["A", "T"],
  ["C", "G"],
  ["G", "C"],
  ["T", "A"],
  ["A", "T"],
  ["G", "C"],
  ["C", "G"],
  ["T", "A"],
] as const;

const SIGNALS = ["ATCG", "OMICS", "MODEL", "VERIFY", "REPORT"];

export function LandingPage() {
  const { t } = useI18n();
  const landing = t.marketing.landing;

  return (
    <div className="landing-redesign min-h-screen scroll-smooth bg-[var(--lab-bg-main)] text-[var(--lab-text-main)]">
      <LandingScrollEffects />
      <SiteHeader />
      <LandingToc />

      <main>
        <section
          id="hero"
          data-landing-section
          className="landing-hero-field relative isolate overflow-hidden px-4 pb-14 pt-14 sm:px-6 sm:pb-20 sm:pt-20 lg:px-8"
        >
          <div className="mx-auto grid min-h-[calc(100dvh-7rem)] max-w-7xl items-center gap-12 lg:grid-cols-[0.88fr_1.12fr]">
            <div className="landing-reveal relative z-10 max-w-3xl">
              <p className="mb-6 inline-flex rounded-[4px] border border-[var(--lab-text-main)]/20 bg-[var(--lab-surface)]/62 px-3 py-1 font-mono text-xs text-[var(--lab-text-muted)]">
                {landing.hero.badge}
              </p>
              <h1 className="max-w-4xl whitespace-pre-line text-balance font-sans text-5xl font-semibold leading-[1.02] sm:text-6xl">
                {landing.hero.headline}
              </h1>
              <p className="mt-6 max-w-xl text-pretty text-lg leading-8 text-[var(--lab-text-sub)] sm:text-xl">
                {landing.hero.subhead}
              </p>
              <div className="mt-9 flex flex-col items-start gap-4 sm:flex-row sm:items-center">
                <Button
                  asChild
                  className="h-12 w-fit rounded-[6px] bg-[var(--lab-accent)] px-5 text-[var(--lab-on-primary)] shadow-[0_7px_0_var(--lab-accent-deep),0_18px_36px_rgb(62_92_67/0.16)] transition-transform hover:-translate-y-0.5 hover:bg-[var(--lab-accent-hover)]"
                >
                  <Link href="/workspace">
                    {t.marketing.nav.tryNow}
                    <ArrowRightIcon className="size-4" />
                  </Link>
                </Button>
                <Link
                  href="#collaboration"
                  className="inline-flex h-12 items-center gap-2 text-sm font-semibold text-[var(--lab-text-main)] underline-offset-4 hover:underline"
                >
                  {t.marketing.nav.readVision}
                  <ArrowRightIcon className="size-4" />
                </Link>
              </div>
            </div>

            <CollaborationAsciiScene />
          </div>
        </section>

        <Section id="collaboration" className="bg-[var(--lab-surface)]">
          <div className="mx-auto grid max-w-7xl gap-12 lg:grid-cols-[0.88fr_1.12fr] lg:items-start">
            <SectionIntro
              eyebrow="collaboration"
              headline={landing.workbench.headline}
              subhead={landing.workbench.body}
            />
            <div className="grid gap-3">
              {landing.workbench.items.map((item, index) => (
                <article
                  key={item.title}
                  className="landing-step-row grid gap-4 border-t border-[var(--lab-border-soft)] py-5 sm:grid-cols-[3.5rem_1fr]"
                >
                  <span className="font-mono text-sm text-[var(--lab-accent)]">
                    0{index + 1}
                  </span>
                  <div>
                    <h3 className="text-xl font-semibold">{item.title}</h3>
                    <p className="mt-2 max-w-2xl text-sm leading-7 text-[var(--lab-text-sub)]">
                      {item.body}
                    </p>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </Section>

        <Section id="workflow" className="bg-[var(--lab-bg-main)]">
          <div className="mx-auto max-w-7xl">
            <SectionIntro
              eyebrow="workflow"
              headline={landing.scenario.headline}
              subhead={landing.scenario.subhead}
            />
            <div className="mt-12 grid gap-4 md:grid-cols-3">
              {landing.scenario.cards.slice(0, 3).map((card, index) => (
                <article
                  key={card.title}
                  className="landing-workflow-card min-h-64 rounded-[8px] border border-[var(--lab-border-soft)] bg-[var(--lab-surface)] p-5"
                >
                  <div className="flex items-center justify-between gap-4 font-mono text-xs text-[var(--lab-text-muted)]">
                    <span>phase 0{index + 1}</span>
                    <CheckCircle2Icon className="size-4 text-[var(--lab-primary)]" />
                  </div>
                  <h3 className="mt-7 text-2xl font-semibold leading-tight">{card.title}</h3>
                  {card.quote ? (
                    <p className="mt-5 border-l border-[var(--lab-accent)] pl-4 font-mono text-sm leading-7 text-[var(--lab-text-main)]">
                      {card.quote}
                    </p>
                  ) : null}
                  <p className="mt-5 text-sm leading-7 text-[var(--lab-text-sub)]">
                    {card.result}
                  </p>
                </article>
              ))}
            </div>
          </div>
        </Section>

        <Section id="capability" className="bg-[var(--lab-ink-dark)] text-[var(--lab-on-dark)]">
          <div className="mx-auto grid max-w-7xl gap-12 lg:grid-cols-[0.95fr_1.05fr] lg:items-start">
            <div>
              <SectionIntro
                eyebrow="capability"
                headline={landing.capability.headline}
                subhead={landing.capability.subhead}
                inverted
              />
              <div className="mt-10 grid gap-3 sm:grid-cols-5 lg:grid-cols-1">
                {landing.compute.agents.map((agent) => (
                  <div
                    key={agent.title}
                    className="grid grid-cols-[5rem_1fr] gap-4 border-t border-white/[0.12] py-4"
                  >
                    <span className="font-mono text-sm text-[var(--lab-cyan)]">
                      {agent.title}
                    </span>
                    <p className="text-sm leading-6 text-[var(--lab-on-dark-muted)]">
                      {agent.body}
                    </p>
                  </div>
                ))}
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-1">
              {landing.capability.columns.map((column) => (
                <article
                  key={column.title}
                  className="rounded-[8px] border border-white/[0.12] bg-white/[0.06] p-5"
                >
                  <div className="flex items-start justify-between gap-5">
                    <p className="font-mono text-5xl leading-none text-[var(--lab-yellow)]">
                      {column.metric}
                    </p>
                    <div className="flex max-w-sm flex-wrap justify-end gap-2">
                      {column.chips.slice(0, 4).map((chip) => (
                        <span
                          key={chip}
                          className="rounded-[4px] border border-white/[0.12] px-2 py-1 font-mono text-[11px] text-[var(--lab-on-dark-muted)]"
                        >
                          {chip}
                        </span>
                      ))}
                    </div>
                  </div>
                  <h3 className="mt-6 text-2xl font-semibold leading-tight">{column.title}</h3>
                  <p className="mt-3 max-w-2xl text-sm leading-7 text-[var(--lab-on-dark-muted)]">
                    {column.body}
                  </p>
                </article>
              ))}
            </div>
          </div>
        </Section>

        <section
          id="cta"
          data-landing-section
          className="landing-reveal px-4 py-20 sm:px-6 lg:px-8"
        >
          <div className="mx-auto max-w-7xl border-t border-[var(--lab-border-soft)] pt-12">
            <div>
              <p className="mb-4 font-mono text-xs text-[var(--lab-text-muted)]">next run</p>
              <h2 className="max-w-4xl text-balance text-4xl font-semibold leading-tight sm:text-5xl">
                {landing.finalCta.headline}
              </h2>
              <p className="mt-5 max-w-2xl text-lg leading-8 text-[var(--lab-text-sub)]">
                {landing.finalCta.subhead}
              </p>
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}

function CollaborationAsciiScene() {
  return (
    <div
      className="landing-reveal landing-ascii-stage relative z-10 min-h-[34rem] overflow-hidden rounded-[8px] border border-[var(--lab-border-soft)] bg-[var(--lab-surface)]/66 p-5 shadow-[0_28px_80px_rgb(40_59_44/0.14)]"
      aria-label="Animated ASCII scene showing biology and an agent collaborating"
    >
      <div className="landing-stage-grid" aria-hidden="true" />
      <div className="landing-dna-column" aria-hidden="true">
        <div className="font-mono text-xs text-[var(--lab-text-muted)]">DNA</div>
        <div className="mt-5 space-y-2">
          {DNA_PAIRS.map(([left, right], index) => (
            <div key={`${left}-${right}-${index}`} className="landing-dna-row">
              <span>{left}</span>
              <span className="landing-dna-rung">---</span>
              <span>{right}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="landing-signal-rail" aria-hidden="true">
        {SIGNALS.map((signal) => (
          <span key={signal} className="landing-signal-token">
            {signal}
          </span>
        ))}
      </div>

      <div className="landing-macintosh" aria-hidden="true">
        <pre>{`+----------------+
|  ST AGENT  01  |
|                |
|   [ o   o ]    |
|      ___       |
|                |
| > read biology |
| > run tools    |
| > cite truth   |
+----------------+
       |  |
   +----------+`}</pre>
        <span className="landing-cursor" />
      </div>

      <div className="landing-stage-caption">
        <span>biology</span>
        <span>agent</span>
        <span>evidence</span>
      </div>
    </div>
  );
}

function Section({
  children,
  className,
  id,
}: {
  children: ReactNode;
  className?: string;
  id: string;
}) {
  return (
    <section
      id={id}
      data-landing-section
      className={cn("landing-reveal px-4 py-20 sm:px-6 lg:px-8", className)}
    >
      {children}
    </section>
  );
}

function SectionIntro({
  eyebrow,
  headline,
  inverted,
  subhead,
}: {
  eyebrow: string;
  headline: string;
  inverted?: boolean;
  subhead: string;
}) {
  return (
    <div>
      <p
        className={cn(
          "mb-5 font-mono text-xs text-[var(--lab-text-muted)]",
          inverted && "text-[var(--lab-on-dark-muted)]",
        )}
      >
        {eyebrow}
      </p>
      <h2
        className={cn(
          "max-w-4xl text-balance text-4xl font-semibold leading-tight sm:text-5xl",
          inverted && "text-[var(--lab-on-dark)]",
        )}
      >
        {headline}
      </h2>
      <p
        className={cn(
          "mt-5 max-w-2xl text-pretty text-lg leading-8 text-[var(--lab-text-sub)]",
          inverted && "text-[var(--lab-on-dark-muted)]",
        )}
      >
        {subhead}
      </p>
    </div>
  );
}
