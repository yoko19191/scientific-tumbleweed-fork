import { SiteHeader } from "@/components/landing/site-header";
import type { Locale } from "@/core/i18n/locale";

export function Header(_props: {
  className?: string;
  homeURL?: string;
  locale?: Locale;
}) {
  return <SiteHeader />;
}
