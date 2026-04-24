"use client";

import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useAuth } from "@/core/auth/AuthProvider";
import { useI18n } from "@/core/i18n/hooks";
import { cn } from "@/lib/utils";

import { AuroraText } from "../ui/aurora-text";

let waved = false;

const QUIPS_ZH = [
  "今天想探索什么？",
  "有什么假设需要验证吗？",
  "需要帮你查文献还是跑数据？",
  "把你的想法告诉我吧。",
  "准备好开始下一个实验了吗？",
  "有什么难题一起想想？",
  "数据跑完了吗？要不要一起看看结果？",
  "论文写到哪了？需要帮忙润色吗？",
  "今天的 p 值还好吗？",
  "要不要帮你画几张图？",
  "实验记录更新了吗？",
  "来，把你的 idea 说出来，我帮你拆解。",
  "需要做个 literature review 吗？",
  "代码跑不通？说说看什么报错。",
  "要不要一起设计个对照实验？",
  "有新数据要分析吗？",
];

const QUIPS_EN = [
  "What shall we explore today?",
  "Any hypotheses to test?",
  "Literature review or data crunching?",
  "Tell me what's on your mind.",
  "Ready for the next experiment?",
  "Got a tough problem? Let's think together.",
  "Data's in — shall we take a look?",
  "How's the manuscript coming along?",
  "How are those p-values looking today?",
  "Want me to whip up some figures?",
  "Lab notebook up to date?",
  "Pitch me your idea — I'll help break it down.",
  "Time for a lit review?",
  "Code acting up? Walk me through the error.",
  "Shall we design a controlled experiment?",
  "Got fresh data to analyze?",
];

function getTimeGreeting(locale: string): string {
  const hour = new Date().getHours();
  if (locale === "zh-CN") {
    if (hour < 6) return "夜深了";
    if (hour < 9) return "早上好";
    if (hour < 12) return "上午好";
    if (hour < 14) return "中午好";
    if (hour < 18) return "下午好";
    if (hour < 22) return "晚上好";
    return "夜深了";
  }
  if (hour < 6) return "Burning the midnight oil";
  if (hour < 12) return "Good morning";
  if (hour < 14) return "Good afternoon";
  if (hour < 18) return "Good afternoon";
  if (hour < 22) return "Good evening";
  return "Burning the midnight oil";
}

export function Welcome({
  className,
  mode,
}: {
  className?: string;
  mode?: "ultra" | "pro" | "thinking" | "flash";
}) {
  const { t, locale } = useI18n();
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const isUltra = useMemo(() => mode === "ultra", [mode]);
  const colors = useMemo(() => {
    if (isUltra) {
      return ["#efefbb", "#e9c665", "#e3a812"];
    }
    return ["var(--color-foreground)"];
  }, [isUltra]);

  const greeting = useMemo(() => {
    const timeGreeting = getTimeGreeting(locale);
    const name = user?.display_name || user?.username || "";
    return name ? `${timeGreeting}，${name}` : timeGreeting;
  }, [locale, user]);

  const quips = useMemo(() => (locale === "zh-CN" ? QUIPS_ZH : QUIPS_EN), [locale]);
  const [quipIndex, setQuipIndex] = useState(() => Math.floor(Math.random() * (locale === "zh-CN" ? QUIPS_ZH.length : QUIPS_EN.length)));
  const [quipFading, setQuipFading] = useState(false);

  const cycleQuip = useCallback(() => {
    setQuipFading(true);
    setTimeout(() => {
      setQuipIndex((prev) => (prev + 1) % quips.length);
      setQuipFading(false);
    }, 200);
  }, [quips.length]);

  const [showQuip, setShowQuip] = useState(false);
  const [waving, setWaving] = useState(false);
  const waveTimeoutRef = useRef<ReturnType<typeof setTimeout>>(null);

  const replayWave = useCallback(() => {
    if (waveTimeoutRef.current) clearTimeout(waveTimeoutRef.current);
    setWaving(true);
    waveTimeoutRef.current = setTimeout(() => setWaving(false), 1200);
  }, []);

  useEffect(() => {
    waved = true;
    const timer = setTimeout(() => setShowQuip(true), 600);
    return () => clearTimeout(timer);
  }, []);

  if (searchParams.get("mode") === "skill") {
    return (
      <div
        className={cn(
          "mx-auto flex w-full flex-col items-center justify-center gap-2 px-8 py-4 text-center",
          className,
        )}
      >
        <div className="text-2xl font-bold">
          {`✨ ${t.welcome.createYourOwnSkill} ✨`}
        </div>
        <div className="text-muted-foreground text-sm">
          {t.welcome.createYourOwnSkillDescription.includes("\n") ? (
            <pre className="font-sans whitespace-pre">
              {t.welcome.createYourOwnSkillDescription}
            </pre>
          ) : (
            <p>{t.welcome.createYourOwnSkillDescription}</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "mx-auto flex w-full flex-col items-center justify-center gap-3 px-8 py-4 text-center font-serif",
        className,
      )}
    >
      <div className="flex items-center gap-3 text-4xl font-bold">
        <button
          type="button"
          className={cn("inline-block cursor-pointer", waving ? "animate-wave" : (!waved ? "animate-wave" : ""))}
          onClick={replayWave}
          aria-label="Wave"
        >
          {isUltra ? "🚀" : "👋"}
        </button>
        <AuroraText colors={colors}>{greeting}</AuroraText>
      </div>
      <button
        type="button"
        onClick={cycleQuip}
        className={cn(
          "text-muted-foreground cursor-pointer border-none bg-transparent text-base italic transition-all duration-300",
          showQuip ? "translate-y-0" : "translate-y-2",
          showQuip && !quipFading ? "opacity-100" : "opacity-0",
        )}
      >
        {quips[quipIndex]}
      </button>
    </div>
  );
}
