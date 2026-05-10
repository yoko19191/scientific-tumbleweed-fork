"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { cn } from "@/lib/utils";

export function CursorTooltip({
  children,
  content,
  delay = 300,
  className,
}: {
  children: React.ReactNode;
  content: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  const [visible, setVisible] = useState(false);
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    },
    [],
  );

  const handleEnter = (e: React.MouseEvent) => {
    const { clientX, clientY } = e;
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setPos({ x: clientX, y: clientY });
      setVisible(true);
    }, delay);
  };

  const handleMove = (e: React.MouseEvent) => {
    if (visible) setPos({ x: e.clientX, y: e.clientY });
  };

  const handleLeave = () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setVisible(false);
    setPos(null);
  };

  return (
    <div
      onMouseEnter={handleEnter}
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      className="contents"
    >
      {children}
      {visible && pos && typeof document !== "undefined"
        ? createPortal(
            <div
              className={cn(
                "pointer-events-none fixed z-50 max-w-xs rounded-md border bg-foreground text-background dark:text-foreground dark:bg-[#050504] dark:border-white/18 px-2 py-1 text-xs shadow-md break-all",
                className,
              )}
              style={{ left: pos.x + 12, top: pos.y + 16 }}
            >
              {content}
            </div>,
            document.body,
          )
        : null}
    </div>
  );
}
