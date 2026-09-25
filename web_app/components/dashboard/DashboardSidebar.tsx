"use client";

import { useTranslations } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
import { LogoMark, PlusIcon, SettingsIcon, VideoIcon, CreditIcon, SparklesIcon } from "@/components/ui/icons";
import { useAuth } from "@/lib/auth/auth-context";
import { Button } from "@/components/ui/Button";

export function DashboardSidebar() {
  const t = useTranslations("dashboard");
  const tApp = useTranslations("app");
  const tAuth = useTranslations("auth");
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const navItems = [
    { href: "/dashboard", label: t("nav.dashboard"), icon: VideoIcon },
    { href: "/dashboard/videos", label: t("nav.videos"), icon: VideoIcon },
    { href: "/dashboard/brand", label: t("nav.brand"), icon: SparklesIcon },
    { href: "/dashboard/packages", label: t("nav.packages"), icon: CreditIcon },
    { href: "/dashboard/settings", label: t("nav.settings"), icon: SettingsIcon },
  ];

  return (
    <aside className="flex h-full w-full flex-col border-r border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-950">
      <div className="flex items-center gap-2 px-4 py-4">
        <LogoMark className="h-6 w-6 text-indigo-600" />
        <span className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
          {tApp("name")}
        </span>
      </div>

      <div className="px-3">
        <Link href="/dashboard/create" className="block">
          <Button size="sm" className="w-full">
            <PlusIcon className="h-4 w-4" />
            {t("createVideo")}
          </Button>
        </Link>
      </div>

      <nav className="mt-4 flex-1 space-y-0.5 px-2" aria-label="Dashboard">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={isActive ? "page" : undefined}
              className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors ${
                isActive
                  ? "bg-neutral-100 font-medium text-neutral-900 dark:bg-neutral-800 dark:text-neutral-100"
                  : "text-neutral-600 hover:bg-neutral-50 dark:text-neutral-400 dark:hover:bg-neutral-900"
              }`}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {user && (
        <div className="border-t border-neutral-200 p-3 dark:border-neutral-800">
          <div className="flex items-center gap-2.5 rounded-lg px-1 py-1.5">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-sm font-semibold text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
              {user.name.charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-neutral-900 dark:text-neutral-100">
                {user.name}
              </p>
              <p className="truncate text-xs text-neutral-500 dark:text-neutral-400">
                {user.email}
              </p>
            </div>
            <button
              type="button"
              onClick={logout}
              className="rounded-md px-2 py-1 text-xs text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900 dark:text-neutral-400 dark:hover:bg-neutral-800 dark:hover:text-neutral-100"
            >
              {tAuth("signOut")}
            </button>
          </div>
        </div>
      )}
    </aside>
  );
}
