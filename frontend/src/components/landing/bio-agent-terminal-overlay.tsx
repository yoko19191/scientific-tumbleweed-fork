"use client";

import { useEffect, useMemo, useState } from "react";

const TERMINAL_LINES: readonly string[] = [
  "ST AGENT BIOS v0.7",
  "phosphor crt online",
  "wetlab bus linked",
  "",
  "> st agent run",
  "goal: biomarkers",
  "> align reads    [ok]",
  "> fold protein   [ok]",
  "> cite evidence  [ok]",
  "> wetlab loop    [run]",
] as const;

const REDUCED_MOTION_LINES: readonly string[] = [
  "ST AGENT // READY",
  "> st agent run",
  "goal: biomarkers",
  "> align reads    [ok]",
  "> fold protein   [ok]",
  "> cite evidence  [ok]",
] as const;

export function BioAgentTerminalOverlay() {
  const [lineIndex, setLineIndex] = useState(0);
  const [charIndex, setCharIndex] = useState(0);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");

    const syncPreference = () => {
      setPrefersReducedMotion(query.matches);
    };

    syncPreference();
    query.addEventListener("change", syncPreference);

    return () => query.removeEventListener("change", syncPreference);
  }, []);

  useEffect(() => {
    if (prefersReducedMotion) {
      return;
    }

    const currentLine = TERMINAL_LINES[lineIndex] ?? "";
    const lineComplete = charIndex >= currentLine.length;
    const sequenceComplete =
      lineIndex === TERMINAL_LINES.length - 1 && lineComplete;

    const delay = sequenceComplete
      ? 2200
      : lineComplete
        ? currentLine === ""
          ? 120
          : 280
        : currentLine[charIndex] === " "
          ? 58
          : 38;

    const timeout = window.setTimeout(() => {
      if (sequenceComplete) {
        setLineIndex(0);
        setCharIndex(0);
        return;
      }

      if (lineComplete) {
        setLineIndex((index) => index + 1);
        setCharIndex(0);
        return;
      }

      setCharIndex((index) => index + 1);
    }, delay);

    return () => window.clearTimeout(timeout);
  }, [charIndex, lineIndex, prefersReducedMotion]);

  const visibleLines = useMemo(() => {
    if (prefersReducedMotion) {
      return REDUCED_MOTION_LINES;
    }

    return TERMINAL_LINES.slice(0, lineIndex)
      .concat((TERMINAL_LINES[lineIndex] ?? "").slice(0, charIndex))
      .slice(-6);
  }, [charIndex, lineIndex, prefersReducedMotion]);

  return (
    <div className="landing-crt-terminal">
      <div className="landing-crt-terminal-glass" />
      <div className="landing-crt-terminal-lines">
        {visibleLines.map((line, index) => (
          <span
            key={`${line === "" ? "blank" : line}-${index}`}
            className={line.startsWith(">") ? "landing-crt-command" : undefined}
          >
            {line}
          </span>
        ))}
        <span className="landing-crt-cursor" />
      </div>
      <div className="landing-crt-scanline" />
    </div>
  );
}
