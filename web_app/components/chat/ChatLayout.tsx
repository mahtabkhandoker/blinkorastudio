"use client";

import { cloneElement, isValidElement, useState, type ReactElement, type ReactNode } from "react";
import { ChatSidebar } from "./ChatSidebar";
import type { ConversationSummary } from "@/lib/chat/types";

export function ChatLayout({
  conversations,
  activeId,
  header,
  children,
  composer,
}: {
  conversations: ConversationSummary[];
  activeId: string;
  header: ReactElement<{ onToggleSidebar?: () => void }>;
  children: ReactNode;
  composer: ReactNode;
}) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const headerWithToggle = isValidElement(header)
    ? cloneElement(header, { onToggleSidebar: () => setMobileNavOpen((v) => !v) })
    : header;

  return (
    <div className="flex h-full w-full overflow-hidden">
      <div className="hidden w-64 shrink-0 lg:block">
        <ChatSidebar conversations={conversations} activeId={activeId} />
      </div>

      {mobileNavOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            type="button"
            aria-label="Close chat history"
            className="absolute inset-0 bg-black/30"
            onClick={() => setMobileNavOpen(false)}
          />
          <div className="relative h-full w-72 max-w-[80vw]">
            <ChatSidebar conversations={conversations} activeId={activeId} />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        {headerWithToggle}
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">{children}</div>
        {composer}
      </div>
    </div>
  );
}
