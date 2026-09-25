"use client";

import { useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { PaperclipIcon } from "@/components/ui/icons";

export function AttachmentButton({
  onFilesSelected,
  disabled,
}: {
  onFilesSelected: (files: FileList) => void;
  disabled?: boolean;
}) {
  const t = useTranslations("chat");
  const [menuOpen, setMenuOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function openPicker() {
    setMenuOpen(false);
    inputRef.current?.click();
  }

  const menuItems = [
    { label: t("uploadImage"), key: "image" },
    { label: t("uploadLogo"), key: "logo" },
    { label: t("uploadProduct"), key: "product" },
    { label: t("uploadOther"), key: "other" },
  ];

  return (
    <div className="relative">
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple
        className="hidden"
        onChange={(e) => {
          if (e.target.files && e.target.files.length > 0) {
            onFilesSelected(e.target.files);
            e.target.value = "";
          }
        }}
      />
      <button
        type="button"
        disabled={disabled}
        onClick={() => setMenuOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={menuOpen}
        aria-label={t("upload")}
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-neutral-500 hover:bg-neutral-100 disabled:opacity-50 dark:text-neutral-400 dark:hover:bg-neutral-800"
      >
        <PaperclipIcon className="h-5 w-5" />
      </button>

      {menuOpen && (
        <>
          <button
            type="button"
            aria-hidden
            tabIndex={-1}
            className="fixed inset-0 z-10 cursor-default"
            onClick={() => setMenuOpen(false)}
          />
          <div
            role="menu"
            className="absolute bottom-11 left-0 z-20 w-48 overflow-hidden rounded-xl border border-neutral-200 bg-white py-1 shadow-lg dark:border-neutral-800 dark:bg-neutral-900"
          >
            {menuItems.map((item) => (
              <button
                key={item.key}
                type="button"
                role="menuitem"
                onClick={openPicker}
                className="block w-full px-3.5 py-2 text-left text-sm text-neutral-700 hover:bg-neutral-50 dark:text-neutral-200 dark:hover:bg-neutral-800"
              >
                {item.label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
