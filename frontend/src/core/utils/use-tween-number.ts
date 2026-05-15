import { animate } from "motion";
import { useEffect, useRef, useState } from "react";

/**
 * Tween a numeric value with motion's command animator.
 *
 * - First mount renders `target` instantly (no startup animation).
 * - Subsequent target changes start from the currently displayed value
 *   (so mid-flight re-targets are smooth, not snappy).
 * - Reduced-motion users skip the tween and see jumps.
 *
 * Returns the live displayed number, suitable for direct rendering
 * via your own formatter (e.g. `formatTokenCount`).
 */
export function useTweenNumber(
  target: number,
  options: {
    /** Tween duration in seconds. Default 0.35. */
    duration?: number;
    /** motion easing string or array. Default "easeOut". */
    ease?: Parameters<typeof animate>[2] extends infer T
      ? T extends { ease?: infer E }
        ? E
        : never
      : never;
  } = {},
): number {
  const { duration = 0.35, ease = "easeOut" } = options;
  const [displayed, setDisplayed] = useState(target);
  const displayedRef = useRef(target);
  const isFirstRef = useRef(true);

  useEffect(() => {
    displayedRef.current = displayed;
  }, [displayed]);

  useEffect(() => {
    if (isFirstRef.current) {
      isFirstRef.current = false;
      displayedRef.current = target;
      setDisplayed(target);
      return;
    }

    if (displayedRef.current === target) return;

    const prefersReducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) {
      displayedRef.current = target;
      setDisplayed(target);
      return;
    }

    const controls = animate(displayedRef.current, target, {
      duration,
      ease,
      onUpdate: (latest) => {
        displayedRef.current = latest;
        setDisplayed(latest);
      },
    });

    return () => {
      controls.stop();
    };
  }, [target, duration, ease]);

  return displayed;
}
