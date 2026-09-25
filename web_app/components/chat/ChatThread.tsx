"use client";

import { useEffect, useRef } from "react";
import { useTranslations } from "next-intl";
import type { ChatMessage } from "@/lib/chat/types";
import { ChatMessageItem, type ChatMessageActions } from "./ChatMessage";
import { AssistantMessage } from "./AssistantMessage";

export function ChatThread({
  messages,
  isAssistantTyping,
  actions,
}: {
  messages: ChatMessage[];
  isAssistantTyping: boolean;
  actions: ChatMessageActions;
}) {
  const t = useTranslations("chat");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, isAssistantTyping]);

  return (
    <div className="mx-auto w-full max-w-3xl flex-1 space-y-4 px-3 py-6 md:px-6">
      {messages.map((message) => (
        <div key={message.id} className="blinkora-message-in">
          <ChatMessageItem message={message} actions={actions} />
        </div>
      ))}

      {isAssistantTyping && (
        <div aria-live="polite" aria-label={t("typing")}>
          <AssistantMessage>
            <span className="flex items-center gap-1">
              <span className="blinkora-typing-dot h-1.5 w-1.5 rounded-full bg-neutral-400" style={{ animationDelay: "0ms" }} />
              <span className="blinkora-typing-dot h-1.5 w-1.5 rounded-full bg-neutral-400" style={{ animationDelay: "150ms" }} />
              <span className="blinkora-typing-dot h-1.5 w-1.5 rounded-full bg-neutral-400" style={{ animationDelay: "300ms" }} />
            </span>
          </AssistantMessage>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
