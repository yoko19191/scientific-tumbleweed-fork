"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type { Locale } from "@/core/i18n";
import type { Translations } from "@/core/i18n/locales/types";
import {
  getCachedTranslations,
  loadTranslations,
} from "@/core/i18n/translations";

export interface I18nContextType {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: Translations;
}

export const I18nContext = createContext<I18nContextType | null>(null);

export function I18nProvider({
  children,
  initialLocale,
}: {
  children: ReactNode;
  initialLocale: Locale;
}) {
  const [locale, setLocale] = useState<Locale>(initialLocale);
  const [t, setTranslations] = useState<Translations>(() =>
    getCachedTranslations(initialLocale),
  );

  const handleSetLocale = useCallback((newLocale: Locale) => {
    setLocale(newLocale);
  }, []);

  useEffect(() => {
    let cancelled = false;

    void loadTranslations(locale).then((translations) => {
      if (!cancelled) {
        setTranslations(translations);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [locale]);

  const value = useMemo(
    () => ({ locale, setLocale: handleSetLocale, t }),
    [handleSetLocale, locale, t],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18nContext() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useI18n must be used within I18nProvider");
  }
  return context;
}
