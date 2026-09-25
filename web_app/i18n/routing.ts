import { defineRouting } from "next-intl/routing";

/**
 * Central i18n route configuration for Blinkora Studio.
 * Bangla is the primary/default locale per product requirements; English is fully supported.
 */
export const routing = defineRouting({
  locales: ["bn", "en"],
  defaultLocale: "bn",
  localePrefix: "always",
});

export type AppLocale = (typeof routing.locales)[number];
