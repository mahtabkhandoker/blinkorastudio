"use client";

import { useRef, useState, type ClipboardEvent, type DragEvent, type KeyboardEvent } from "react";
import { useTranslations } from "next-intl";
import { AttachmentButton } from "./AttachmentButton";
import { SendIcon } from "@/components/ui/icons";

export function ChatComposer({
  onSendText,
  onFilesSelected,
  disabled,
}: {
  onSendText: (text: string) => void;
  onFilesSelected: (files: FileList | File[]) => void;
  disabled?: boolean;
}) {
  const t = useTranslations("chat");
  const [value, setValue] = useState("");
  const [isDragOver, setIsDragOver] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function handleSend() {
    const text = value.trim();
    if (!text || disabled) return;
    onSendText(text);
    setValue("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  }

  function handlePaste(event: ClipboardEvent<HTMLTextAreaElement>) {
    const files = Array.from(event.clipboardData.files);
    if (files.length > 0) {
      event.preventDefault();
      onFilesSelected(files);
    }
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragOver(false);
    if (event.dataTransfer.files.length > 0) {
      onFilesSelected(event.dataTransfer.files);
    }
  }

  return (
    <div
      className={`sticky bottom-0 border-t bg-white/95 px-3 py-3 backdrop-blur transition-colors dark:bg-neutral-950/95 md:px-6 ${
        isDragOver
          ? "border-indigo-400 bg-indigo-50/60 dark:bg-indigo-950/30"
          : "border-neutral-200 dark:border-neutral-800"
      }`}
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragOver(true);
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={handleDrop}
    >
      <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border border-neutral-200 bg-white px-2 py-2 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
        <AttachmentButton onFilesSelected={onFilesSelected} disabled={disabled} />
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            e.target.style.height = "auto";
            e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
          }}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          disabled={disabled}
          rows={1}
          placeholder={t("placeholder")}
          aria-label={t("placeholder")}
          className="max-h-40 flex-1 resize-none bg-transparent py-1.5 text-sm text-neutral-900 outline-none placeholder:text-neutral-400 disabled:opacity-50 dark:text-neutral-100"
        />
        <button
          type="button"
          onClick={handleSend}
          disabled={disabled || !value.trim()}
          aria-label={t("send")}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-neutral-900 text-white transition-colors hover:bg-neutral-800 disabled:cursor-not-allowed disabled:bg-neutral-300 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200"
        >
          <SendIcon className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
