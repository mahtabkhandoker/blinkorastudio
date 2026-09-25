"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { ChatLayout } from "@/components/chat/ChatLayout";
import { ChatHeader } from "@/components/chat/ChatHeader";
import { ChatThread } from "@/components/chat/ChatThread";
import { ChatComposer } from "@/components/chat/ChatComposer";
import type { ChatMessageActions } from "@/components/chat/ChatMessage";
import { useChatController } from "@/lib/chat/use-chat-controller";
import { listConversations } from "@/lib/chat/conversation-store";
import { generateId } from "@/lib/chat/id";
import type { ConversationSummary, MissingField } from "@/lib/chat/types";

function titleFromInput(fallback: string, businessName?: string, campaignType?: string) {
  if (businessName && campaignType) return `${businessName} — ${campaignType}`;
  if (businessName) return businessName;
  return fallback;
}

function CreateVideoContent() {
  const t = useTranslations("chat");
  const searchParams = useSearchParams();
  const router = useRouter();

  // A conversation id can come from the URL (resuming/switching chats) or be
  // freshly minted for a brand-new chat; this mirrors `?c=<id>` the sidebar
  // and dashboard links already use. A lazy useState initializer (rather than
  // a ref) keeps this a normal, render-participating value.
  const [conversationId] = useState<string>(() => searchParams.get("c") || generateId("conv"));

  const controller = useChatController(t, conversationId, "New Video");
  const [conversations, setConversations] = useState<ConversationSummary[]>(() => listConversations());

  useEffect(() => {
    // Re-reads the local conversation index (an external store backed by
    // localStorage) whenever this conversation's stage/message count
    // changes. A useSyncExternalStore subscription would be the more
    // "pure" fix, but is overkill for this mock/local persistence layer.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setConversations(listConversations());
  }, [controller.state.stage, controller.state.messages.length]);

  useEffect(() => {
    if (!searchParams.get("c")) {
      router.replace(`/dashboard/create?c=${conversationId}`);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const answeredQuickReplyIds = useMemo(() => {
    const ids = new Set<string>();
    controller.state.messages.forEach((m, index) => {
      if (m.kind !== "question" || !m.quickReplies) return;
      const answeredAfter = controller.state.messages
        .slice(index + 1)
        .some((later) => later.role === "user");
      if (answeredAfter) ids.add(m.id);
    });
    return ids;
  }, [controller.state.messages]);

  const actions: ChatMessageActions = {
    conversationId,
    answeredQuickReplyIds,
    onQuickReply: (_messageId, field, optionId, label) => {
      controller.sendQuickReply(field as MissingField | "suggestion", optionId, label);
    },
    onReplaceAsset: (assetId) => controller.replaceAsset(assetId),
    onAcceptAssetAnyway: (assetId) => controller.acceptAssetAnyway(assetId),
    onEditBrief: () => controller.editBrief(),
    onConfirmBrief: () => controller.confirmBrief(),
    onConfirmGeneration: () => controller.startGeneration(false),
    onRetryGeneration: () => controller.retryGeneration(),
    onFollowUp: (label, patch) => controller.requestRevision(label, patch),
  };

  const status: ConversationSummary["status"] =
    controller.state.stage === "FAILED"
      ? "failed"
      : controller.state.stage === "RESULT"
        ? "completed"
        : controller.state.stage === "GENERATING" || controller.state.stage === "QUALITY_CHECK"
          ? "generating"
          : "active";

  const displayTitle = titleFromInput(
    controller.state.title,
    controller.state.creativeInput.businessName,
    controller.state.creativeInput.campaignType,
  );

  return (
    <ChatLayout
      conversations={conversations}
      activeId={conversationId}
      header={<ChatHeader title={displayTitle} status={status} />}
      composer={
        <ChatComposer
          onSendText={controller.sendText}
          onFilesSelected={controller.uploadFiles}
          disabled={controller.state.stage === "GENERATING"}
        />
      }
    >
      <ChatThread
        messages={controller.state.messages}
        isAssistantTyping={controller.isUploading}
        actions={actions}
      />
    </ChatLayout>
  );
}

export default function CreateVideoPage() {
  return (
    <Suspense fallback={null}>
      <CreateVideoContent />
    </Suspense>
  );
}
