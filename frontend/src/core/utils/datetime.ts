import {
  format,
  formatDistanceToNow,
  isThisYear,
  isToday,
  isYesterday,
} from "date-fns";
import { enUS as dateFnsEnUS, zhCN as dateFnsZhCN } from "date-fns/locale";

import { detectLocale, type Locale } from "@/core/i18n";
import { getLocaleFromCookie } from "@/core/i18n/cookies";

function getDateFnsLocale(locale: Locale) {
  switch (locale) {
    case "zh-CN":
      return dateFnsZhCN;
    case "en-US":
    default:
      return dateFnsEnUS;
  }
}

// Threshold separating epoch-seconds from epoch-milliseconds.
// 1e12 ms ≈ 2001-09-09; any "seconds" timestamp in our era is well below it,
// any reasonable "milliseconds" timestamp is well above it.
const EPOCH_SECONDS_MAX = 1e12;

/**
 * Robustly coerce a timestamp-like input into a Date.
 *
 * The backend serializes ``time.time()`` directly (e.g. ``"1778734481.071336"``)
 * for ``updated_at``, which ``new Date(str)`` parses as Invalid Date. Here we
 * accept ISO strings, numeric strings (epoch seconds with optional fraction or
 * epoch milliseconds), numbers, and Date instances, returning ``null`` for
 * anything we cannot interpret.
 */
function toDate(input: Date | string | number | null | undefined): Date | null {
  if (input == null || input === "") return null;
  if (input instanceof Date) {
    return Number.isNaN(input.getTime()) ? null : input;
  }
  if (typeof input === "number") {
    if (!Number.isFinite(input)) return null;
    const ms = input < EPOCH_SECONDS_MAX ? input * 1000 : input;
    const d = new Date(ms);
    return Number.isNaN(d.getTime()) ? null : d;
  }
  const s = input.trim();
  if (s === "") return null;
  if (/^-?\d+(\.\d+)?$/.test(s)) {
    const n = Number(s);
    if (!Number.isFinite(n)) return null;
    const ms = n < EPOCH_SECONDS_MAX ? n * 1000 : n;
    const d = new Date(ms);
    return Number.isNaN(d.getTime()) ? null : d;
  }
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function formatTimeAgo(
  date: Date | string | number | null | undefined,
  locale?: Locale,
) {
  const d = toDate(date);
  if (!d) return "";
  const effectiveLocale =
    locale ??
    (getLocaleFromCookie() as Locale | null) ??
    // Fallback when cookie is missing (or on first render)
    detectLocale();
  return formatDistanceToNow(d, {
    addSuffix: true,
    locale: getDateFnsLocale(effectiveLocale),
  });
}

export function formatThreadTimestamp(
  date: Date | string | number | null | undefined,
  locale: Locale,
  yesterdayLabel: string,
): string {
  const d = toDate(date);
  if (!d) return "";

  const dfLocale = getDateFnsLocale(locale);
  if (isToday(d)) return format(d, "HH:mm");
  if (isYesterday(d)) return yesterdayLabel;
  if (isThisYear(d)) {
    return locale === "zh-CN"
      ? format(d, "M/d")
      : format(d, "MMM d", { locale: dfLocale });
  }
  return locale === "zh-CN"
    ? format(d, "yyyy/M/d")
    : format(d, "MMM d, yyyy", { locale: dfLocale });
}
