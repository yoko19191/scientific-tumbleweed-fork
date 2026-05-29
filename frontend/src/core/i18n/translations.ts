import { DEFAULT_LOCALE, type Locale } from "./locale";
import { enUS } from "./locales/en-US";
import type { Translations } from "./locales/types";

const translationCache: Partial<Record<Locale, Translations>> = {
  "en-US": enUS,
};

const localeLoaders: Record<Locale, () => Promise<Translations>> = {
  "en-US": async () => enUS,
  "zh-CN": async () => {
    const locale = await import("./locales/zh-CN");
    return locale.zhCN;
  },
};

export const fallbackTranslations = enUS;

export function getCachedTranslations(locale: Locale): Translations {
  return (
    translationCache[locale] ??
    translationCache[DEFAULT_LOCALE] ??
    fallbackTranslations
  );
}

export async function loadTranslations(locale: Locale): Promise<Translations> {
  const cached = translationCache[locale];
  if (cached) {
    return cached;
  }
  const loaded = await localeLoaders[locale]();
  translationCache[locale] = loaded;
  return loaded;
}
