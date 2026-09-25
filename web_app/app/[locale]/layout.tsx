import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getMessages, setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { routing } from "@/i18n/routing";
import { AuthProvider } from "@/lib/auth/auth-context";
import { PackageProvider } from "@/lib/package/package-context";
import "../globals.css";

// NOTE: next/font/google (Geist, Hind Siliguri, etc.) requires reaching
// fonts.googleapis.com at build time, which isn't available in every build
// environment (it wasn't in this one). Using a system font stack instead
// keeps the build hermetic; swap in next/font/google or next/font/local
// once a specific brand typeface is chosen and the build environment can
// fetch it (or the font files are vendored locally).

export const metadata: Metadata = {
  title: "Blinkora Studio",
  description: "Create your marketing video by chatting with Blinkora Studio.",
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function RootLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!routing.locales.includes(locale as (typeof routing.locales)[number])) {
    notFound();
  }

  setRequestLocale(locale);
  const messages = await getMessages();

  return (
    <html lang={locale} className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-neutral-50 text-neutral-900 dark:bg-neutral-950 dark:text-neutral-100">
        <NextIntlClientProvider messages={messages}>
          <AuthProvider>
            <PackageProvider>{children}</PackageProvider>
          </AuthProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
