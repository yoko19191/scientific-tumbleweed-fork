"use client";

import {
  ArrowRightIcon,
  BadgeCheckIcon,
  BlocksIcon,
  BookOpenIcon,
  BotIcon,
  BrainCircuitIcon,
  ChartNoAxesCombinedIcon,
  CheckCircle2Icon,
  Code2Icon,
  DatabaseIcon,
  FlaskConicalIcon,
  GitBranchIcon,
  LockKeyholeIcon,
  MessageCircleIcon,
  MicroscopeIcon,
  NetworkIcon,
  SearchIcon,
  ShieldCheckIcon,
  TerminalIcon,
} from "lucide-react";
import Link from "next/link";

import { LandingToc } from "@/components/landing/landing-toc";
import { LandingScrollEffects } from "@/components/landing/scroll-effects";
import { SiteFooter } from "@/components/landing/site-footer";
import { SiteHeader } from "@/components/landing/site-header";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/core/i18n/hooks";
import { cn } from "@/lib/utils";

const WORKBENCH_ICONS = [MessageCircleIcon, DatabaseIcon, TerminalIcon];
const SCENARIO_ICONS = [
  MicroscopeIcon,
  GitBranchIcon,
  FlaskConicalIcon,
  BookOpenIcon,
];
const CAPABILITY_ICONS = [DatabaseIcon, BookOpenIcon, ChartNoAxesCombinedIcon];
const AGENT_ICONS = [BrainCircuitIcon, SearchIcon, GitBranchIcon, Code2Icon, ShieldCheckIcon];
const TRUST_ICONS = [BadgeCheckIcon, LockKeyholeIcon, BlocksIcon];

const RESEARCH_STEPS = [
  { label: "问题定义", sub: "研究方向" },
  { label: "已有证据整合", sub: "文献数据经验" },
  { label: "假设生成", sub: "规定搜索空间" },
  { label: "生信/计算生物学", sub: "缩小搜索空间" },
  { label: "实验扰动", sub: "反事实干预" },
  { label: "结果分析/机制解释", sub: "证据链条" },
  { label: "发表/转化", sub: "" },
];

export function LandingPage() {
  const { t } = useI18n();
  const landing = t.marketing.landing;

  return (
    <div className="min-h-screen scroll-smooth bg-[var(--lab-bg-main)] text-[var(--lab-text-main)]">
      <LandingScrollEffects />
      <SiteHeader />
      <LandingToc />

      <main>
        <section
          id="hero"
          data-landing-section
          className="relative isolate flex min-h-[calc(100vh-4rem)] items-center overflow-hidden px-4 py-20 sm:px-6 lg:px-8"
        >
          <div className="absolute inset-0 -z-20 bg-[url('/landing/biomed-hero.png')] bg-cover bg-center" />
          <div className="absolute inset-0 -z-10 bg-[linear-gradient(90deg,hsla(210,18%,14%,0.88),hsla(210,18%,14%,0.74)_44%,hsla(210,18%,14%,0.26))]" />
          <div className="mx-auto w-full max-w-7xl">
            <div className="landing-reveal max-w-4xl">
              <p className="mb-7 inline-flex rounded-full border border-[var(--lab-on-dark)]/50 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.18em] text-[var(--lab-on-dark)]/86">
                Scientific Tumbleweed Lab
              </p>
              <h1 className="whitespace-pre-line font-serif text-6xl font-semibold leading-[0.98] tracking-tight text-[var(--lab-on-dark)] sm:text-7xl lg:text-8xl">
                {landing.hero.headline}
                <sup className="ml-3 inline-flex translate-y-[-0.7em] rounded-full border border-current px-2 py-1 align-super font-mono text-[10px] font-normal uppercase tracking-[0.18em] text-[var(--lab-on-dark-muted)] sm:text-[11px]">
                  {landing.hero.badge}
                </sup>
              </h1>
              <p className="mt-7 max-w-2xl whitespace-pre-line text-xl leading-8 text-[var(--lab-on-dark-muted)] sm:text-2xl">
                {landing.hero.subhead}
              </p>
              <div className="mt-10 flex flex-col gap-4 sm:flex-row sm:items-center">
                <Button
                  asChild
                  className="h-12 bg-[var(--lab-accent)] px-6 text-white shadow-[0_8px_0_var(--lab-accent-deep),0_20px_40px_hsla(210,30%,20%,0.22)] hover:-translate-y-0.5 hover:bg-[var(--lab-accent-hover)]"
                >
                  <Link href="/workspace">
                    {t.marketing.nav.tryNow}
                    <ArrowRightIcon className="size-4" />
                  </Link>
                </Button>
                <Link
                  href="#method"
                  className="inline-flex h-12 items-center gap-2 text-sm font-semibold text-[var(--lab-on-dark)] underline-offset-4 hover:underline"
                >
                  {t.marketing.nav.readVision}
                  <ArrowRightIcon className="size-4" />
                </Link>
              </div>
            </div>
          </div>
        </section>

        <Section id="workbench" className="bg-[var(--lab-bg-sub)]">
          <div className="mx-auto max-w-5xl text-center">
            <h2 className="font-serif text-4xl font-semibold tracking-tight text-[var(--lab-text-main)] sm:text-5xl">
              {landing.workbench.headline}
            </h2>
            <p className="mx-auto mt-7 max-w-4xl text-lg leading-9 text-[var(--lab-text-sub)]">
              {landing.workbench.body}
            </p>
          </div>

          {/* Research Pipeline */}
          <div className="mx-auto mt-14 max-w-6xl overflow-x-auto">
            <div className="relative flex min-w-[800px] justify-between px-6">
              <div className="absolute left-6 right-6 top-[9px] h-px bg-[var(--lab-border)]" />
              {RESEARCH_STEPS.map((step) => (
                <div key={step.label} className="relative flex flex-col items-center">
                  <div className="z-10 size-[18px] rounded-full border-[2.5px] border-[var(--lab-primary)] bg-[var(--lab-bg-sub)]" />
                  <span className="mt-3 whitespace-nowrap text-sm font-semibold text-[var(--lab-text-main)]">
                    {step.label}
                  </span>
                  {step.sub ? (
                    <span className="mt-0.5 whitespace-nowrap text-xs text-[var(--lab-text-muted)]">
                      {step.sub}
                    </span>
                  ) : null}
                </div>
              ))}
            </div>
          </div>

          <div className="mx-auto mt-12 grid max-w-5xl gap-4 md:grid-cols-3">
            {landing.workbench.items.map((item, index) => {
              const Icon = WORKBENCH_ICONS[index] ?? MessageCircleIcon;
              return (
                <article
                  key={item.title}
                  className="rounded-lg border border-[var(--lab-border-soft)] bg-[var(--lab-surface)] p-6 text-center shadow-[0_8px_28px_hsla(210,30%,20%,0.06)]"
                >
                  <Icon className="mx-auto mb-5 size-7 text-[var(--lab-primary)]" />
                  <h3 className="font-serif text-xl font-semibold text-[var(--lab-text-main)]">
                    {item.title}
                  </h3>
                  <p className="mt-3 text-sm leading-7 text-[var(--lab-text-sub)]">{item.body}</p>
                </article>
              );
            })}
          </div>
        </Section>

        <Section id="scenario">
          <SectionHeader
            headline={landing.scenario.headline}
            subhead={landing.scenario.subhead}
          />
          <div className="mx-auto mt-12 grid max-w-7xl gap-5 lg:grid-cols-2">
            {landing.scenario.cards.map((card, index) => {
              const Icon = SCENARIO_ICONS[index] ?? MicroscopeIcon;
              return (
                <article
                  key={card.title}
                  className="group rounded-lg border border-[var(--lab-border-soft)] bg-[var(--lab-surface)] p-6 shadow-[0_8px_28px_hsla(210,30%,20%,0.06)] transition-all hover:-translate-y-1 hover:shadow-[0_18px_40px_hsla(210,30%,20%,0.1)]"
                >
                  <Icon className="mb-5 size-6 text-[var(--lab-primary)]" />
                  <h3 className="font-serif text-2xl font-semibold text-[var(--lab-text-main)]">
                    {card.title}
                  </h3>
                  <p className="mt-5 border-l-2 border-[var(--lab-accent)] pl-5 font-serif text-xl leading-8 text-[var(--lab-text-main)]">
                    {card.quote}
                  </p>
                  <p className="mt-5 text-sm leading-7 text-[var(--lab-text-sub)]">
                    {card.result}
                  </p>
                </article>
              );
            })}
          </div>
          <p className="mx-auto mt-10 max-w-3xl text-center text-sm leading-7 text-[var(--lab-text-muted)]">
            {landing.scenario.note}
          </p>
        </Section>

        <Section id="capability" className="bg-[var(--lab-bg-sub)]">
          <SectionHeader
            headline={landing.capability.headline}
            subhead={landing.capability.subhead}
          />
          <div className="mx-auto mt-12 grid max-w-7xl overflow-hidden rounded-lg border border-[var(--lab-border-soft)] bg-[var(--lab-surface)] lg:grid-cols-3">
            {landing.capability.columns.map((column, index) => {
              const Icon = CAPABILITY_ICONS[index] ?? DatabaseIcon;
              return (
                <article
                  key={column.title}
                  className="border-b border-[var(--lab-border-soft)] p-7 last:border-b-0 lg:border-b-0 lg:border-r lg:last:border-r-0"
                >
                  <div className="flex items-center justify-between gap-4">
                    <p className="font-serif text-7xl font-semibold leading-none text-[var(--lab-primary)]">
                      {column.metric}
                    </p>
                    <Icon className="size-7 text-[var(--lab-success)]" />
                  </div>
                  <h3 className="mt-6 font-serif text-2xl font-semibold leading-tight text-[var(--lab-text-main)]">
                    {column.title}
                  </h3>
                  <p className="mt-4 text-sm leading-7 text-[var(--lab-text-sub)]">{column.body}</p>
                  <div className="mt-6 flex flex-wrap gap-2">
                    {column.chips.map((chip) => (
                      <span
                        key={chip}
                        className="rounded-full border border-[var(--lab-border-soft)] bg-[var(--lab-surface-strong)] px-2.5 py-1 font-mono text-[11px] text-[var(--lab-text-sub)]"
                      >
                        {chip}
                      </span>
                    ))}
                  </div>
                </article>
              );
            })}
          </div>
          <div className="mx-auto mt-8 grid max-w-7xl gap-3 md:grid-cols-2 lg:grid-cols-4">
            {landing.capability.workflows.map((workflow) => (
              <Link
                key={workflow.label}
                href="/use-case"
                className="rounded-md border border-[var(--lab-border-soft)] bg-[var(--lab-bg-main)] p-4 transition-colors hover:border-[var(--lab-primary)] hover:bg-[var(--lab-surface)]"
              >
                <p className="font-mono text-xs uppercase tracking-[0.14em] text-[var(--lab-accent)]">
                  {workflow.label}
                </p>
                <p className="mt-2 text-sm text-[var(--lab-text-sub)]">{workflow.text}</p>
              </Link>
            ))}
          </div>
          <p className="mx-auto mt-10 max-w-4xl text-center text-sm leading-7 text-[var(--lab-text-muted)]">
            {landing.capability.note}
          </p>
        </Section>

        <Section id="compute">
          <SectionHeader
            headline={landing.compute.headline}
            subhead={landing.compute.subhead}
          />
          <div className="mx-auto mt-12 grid max-w-7xl gap-5 lg:grid-cols-2">
            <article className="rounded-lg border border-[var(--lab-ink-dark-border)] bg-[var(--lab-ink-dark)] p-6 text-[var(--lab-on-dark)] shadow-[0_18px_48px_hsla(210,30%,20%,0.2)]">
              <TerminalIcon className="mb-5 size-7 text-[var(--lab-cyan)]" />
              <h3 className="font-serif text-2xl font-semibold">
                {landing.compute.sandboxTitle}
              </h3>
              <pre className="mt-6 overflow-x-auto rounded-md border border-[var(--lab-ink-dark-border)] bg-[hsl(210,18%,10%)] p-5 font-mono text-xs leading-7 text-[var(--lab-on-dark-muted)] sm:text-sm">
{`$ which STAR samtools scanpy Rscript xelatex
/opt/bioinfo/bin/STAR
/opt/bioinfo/bin/samtools
/usr/bin/scanpy
/usr/bin/Rscript
/usr/bin/xelatex`}
              </pre>
              <p className="mt-5 text-sm leading-7 text-[var(--lab-on-dark-muted)]">
                {landing.compute.sandboxBody}
              </p>
            </article>
            <article className="rounded-lg border border-[var(--lab-border-soft)] bg-[var(--lab-surface)] p-6 shadow-[0_8px_28px_hsla(210,30%,20%,0.06)]">
              <BotIcon className="mb-5 size-7 text-[var(--lab-purple)]" />
              <h3 className="font-serif text-2xl font-semibold text-[var(--lab-text-main)]">
                {landing.compute.intelligenceTitle}
              </h3>
              <div className="mt-7 grid gap-3 sm:grid-cols-5">
                {landing.compute.agents.map((agent, index) => {
                  const Icon = AGENT_ICONS[index] ?? BrainCircuitIcon;
                  return (
                    <div
                      key={agent.title}
                      className="rounded-md border border-[var(--lab-border-soft)] bg-[var(--lab-surface-strong)] p-3"
                    >
                      <Icon className="mb-4 size-5 text-[var(--lab-primary)]" />
                      <p className="font-serif text-lg font-semibold text-[var(--lab-text-main)]">
                        {agent.title}
                      </p>
                      <p className="mt-2 text-xs leading-5 text-[var(--lab-text-sub)]">{agent.body}</p>
                    </div>
                  );
                })}
              </div>
            </article>
          </div>
          <p className="mx-auto mt-10 max-w-3xl text-center font-serif text-2xl leading-9 text-[var(--lab-text-main)]">
            {landing.compute.note}
          </p>
        </Section>

        <Section id="different" className="bg-[var(--lab-bg-sub)]">
          <SectionHeader headline={landing.different.headline} />
          <div className="mx-auto mt-12 max-w-6xl overflow-hidden rounded-lg border border-[var(--lab-border-soft)] bg-[var(--lab-surface)]">
            <div className="grid grid-cols-[1fr_1fr_1fr] border-b border-[var(--lab-border-soft)] bg-[var(--lab-surface-strong)] p-4 font-mono text-xs uppercase tracking-[0.14em] text-[var(--lab-text-muted)]">
              <span />
              <span>Generic chat assistants</span>
              <span>Scientific Tumbleweed</span>
            </div>
            {landing.different.rows.map((row) => (
              <div
                key={row.label}
                className="grid grid-cols-1 gap-3 border-b border-[var(--lab-border-soft)] p-4 last:border-b-0 md:grid-cols-[1fr_1fr_1fr]"
              >
                <p className="font-semibold text-[var(--lab-text-main)]">{row.label}</p>
                <p className="text-sm leading-7 text-[var(--lab-text-muted)]">{row.generic}</p>
                <p className="text-sm font-medium leading-7 text-[var(--lab-primary)]">
                  {row.tumbleweed}
                </p>
              </div>
            ))}
          </div>
          <p className="mx-auto mt-10 max-w-3xl text-center text-sm leading-7 text-[var(--lab-text-muted)]">
            {landing.different.note}
          </p>
        </Section>

        <section
          id="method"
          data-landing-section
          className="landing-reveal bg-[var(--lab-ink-dark)] px-4 py-20 text-[var(--lab-on-dark)] sm:px-6 lg:px-8"
        >
          <div className="mx-auto max-w-5xl">
            <h2 className="font-serif text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
              {landing.method.headline}
            </h2>
            <p className="mt-5 max-w-2xl text-[var(--lab-on-dark-muted)]">{landing.method.subhead}</p>
            <details className="mt-8 group">
              <summary className="inline-flex cursor-pointer list-none items-center gap-2 rounded-md border border-[var(--lab-ink-dark-border)] px-4 py-3 font-mono text-xs uppercase tracking-[0.14em] text-[var(--lab-on-dark-muted)]">
                {landing.method.trigger}
                <ArrowRightIcon className="size-4 transition-transform group-open:rotate-90" />
              </summary>
              <div className="mt-8 grid gap-4 md:grid-cols-2">
                {landing.method.acts.map((act) => (
                  <article key={act.title} className="rounded-lg border border-white/10 bg-white/6 p-5">
                    <h3 className="font-serif text-xl font-semibold">{act.title}</h3>
                    <p className="mt-3 text-sm leading-7 text-[var(--lab-on-dark-muted)]">{act.body}</p>
                  </article>
                ))}
              </div>
            </details>
            <blockquote className="mt-12 max-w-4xl font-serif text-3xl leading-tight text-[var(--lab-on-dark)] sm:text-4xl">
              “{landing.method.quote}”
            </blockquote>
          </div>
        </section>

        <Section id="trusted">
          <SectionHeader headline={landing.trusted.headline} />
          <div className="mx-auto mt-12 grid max-w-6xl gap-5 md:grid-cols-3">
            {landing.trusted.cards.map((card, index) => {
              const Icon = TRUST_ICONS[index] ?? CheckCircle2Icon;
              return (
                <article
                  key={card.title}
                  className="rounded-lg border border-[var(--lab-border-soft)] bg-[var(--lab-surface)] p-6 shadow-[0_8px_28px_hsla(210,30%,20%,0.06)]"
                >
                  <Icon className="mb-5 size-7 text-[var(--lab-success)]" />
                  <h3 className="font-serif text-2xl font-semibold text-[var(--lab-text-main)]">
                    {card.title}
                  </h3>
                  <p className="mt-3 text-sm leading-7 text-[var(--lab-text-sub)]">{card.body}</p>
                </article>
              );
            })}
          </div>
          <div className="mx-auto mt-10 flex max-w-5xl flex-wrap justify-center gap-2">
            {landing.trusted.badges.map((badge) => (
              <span
                key={badge}
                className="rounded-full border border-[var(--lab-border-soft)] bg-[var(--lab-bg-sub)] px-3 py-1.5 font-mono text-xs text-[var(--lab-text-muted)]"
              >
                {badge}
              </span>
            ))}
          </div>
        </Section>

        <section
          id="cta"
          data-landing-section
          className="landing-reveal relative overflow-hidden px-4 py-24 sm:px-6 lg:px-8"
        >
          <div className="absolute inset-0 -z-20 bg-[url('/landing/biomed-cta.png')] bg-cover bg-center" />
          <div className="absolute inset-0 -z-10 bg-[var(--lab-bg-sub)]/82" />
          <div className="mx-auto max-w-4xl text-center">
            <NetworkIcon className="mx-auto mb-6 size-9 text-[var(--lab-primary)]" />
            <h2 className="font-serif text-5xl font-semibold leading-tight tracking-tight text-[var(--lab-text-main)] sm:text-6xl">
              {landing.finalCta.headline}
            </h2>
            <p className="mx-auto mt-5 max-w-2xl text-lg leading-8 text-[var(--lab-text-sub)]">
              {landing.finalCta.subhead}
            </p>
            <div className="mt-10 flex flex-col justify-center gap-4 sm:flex-row">
              <Button
                asChild
                className="h-12 bg-[var(--lab-accent)] px-6 text-white shadow-[0_8px_0_var(--lab-accent-deep)] hover:-translate-y-0.5 hover:bg-[var(--lab-accent-hover)]"
              >
                <Link href="/workspace">
                  {t.marketing.nav.tryNow}
                  <ArrowRightIcon className="size-4" />
                </Link>
              </Button>
              <Button asChild variant="outline" className="h-12 border-[var(--lab-primary)] bg-[var(--lab-surface)] px-6 text-[var(--lab-primary)]">
                <Link href="/about">{t.marketing.nav.talkToUs}</Link>
              </Button>
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}

function Section({
  children,
  className,
  id,
}: {
  children: React.ReactNode;
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

function SectionHeader({
  headline,
  subhead,
}: {
  headline: string;
  subhead?: string;
}) {
  return (
    <div className="mx-auto max-w-4xl text-center">
      <h2 className="font-serif text-4xl font-semibold leading-tight tracking-tight text-[var(--lab-text-main)] sm:text-5xl">
        {headline}
      </h2>
      {subhead ? (
        <p className="mx-auto mt-5 max-w-3xl text-lg leading-8 text-[var(--lab-text-sub)]">
          {subhead}
        </p>
      ) : null}
    </div>
  );
}
