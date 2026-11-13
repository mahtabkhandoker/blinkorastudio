"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
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
import { OrderFlow } from "@/components/order/OrderFlow";
import { getOrderApiUrl, type Locale } from "@/lib/api/orders";
import { useAuth } from "@/lib/auth/auth-context";
import { listOrderPointers, summaryStatus, toSummaries } from "@/lib/order/order-index";
import { useOrderController } from "@/lib/order/use-order-controller";

function titleFromInput(fallback: string, businessName?: string, campaignType?: string) {
  if (businessName && campaignType) return `${businessName} — ${campaignType}`;
  if (businessName) return businessName;
  return fallback;
}

/**
 * Order flow: used whenever a backend is configured. The backend owns the
 * order; this page only renders it. There is no local fallback, so a
 * backend outage shows an error instead of a pretend order.
 */
function OrderContent({ apiUrl }: { apiUrl: string }) {
  const t = useTranslations("chat");
  const locale = useLocale() as Locale;
  const searchParams = useSearchParams();
  const router = useRouter();
  const { user } = useAuth();
  const orderId = searchParams.get("o");

  const controller = useOrderController({
    apiUrl,
    locale,
    orderId,
    customerRef: user?.id,
    onOrderCreated: (id) => router.replace(`/dashboard/create?o=${id}`),
  });

  const [history, setHistory] = useState<ConversationSummary[]>(() => toSummaries(listOrderPointers()));
  const order = controller.order;
  useEffect(() => {
    // The pointer list lives in localStorage (an external store); re-read
    // it when this order's title or status changes.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setHistory(toSummaries(listOrderPointers()));
  }, [order?.id, order?.status, order?.title]);

  const title = order ? `${order.title === order.number ? t("newVideo") : order.title} · ${order.number}` : t("newVideo");

  return (
    <ChatLayout
      conversations={history}
      activeId={order?.id ?? ""}
      hrefFor={(id) => `/dashboard/create?o=${id}`}
      header={<ChatHeader title={title} status={order ? summaryStatus(order.status) : "active"} />}
      composer={null}
    >
      <OrderFlow controller={controller} />
    </ChatLayout>
  );
}

/**
 * Legacy local chat, kept only as a clearly labelled demo for when no
 * backend is configured. Nothing in it is saved and its video is a sample.
 */
function LegacyDemoContent() {
  const t = useTranslations("chat");
  const tOrder = useTranslations("order");
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
      <p
        role="note"
        className="mx-auto mt-4 w-full max-w-3xl rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200"
      >
        {tOrder("demoBanner")}
      </p>
      <ChatThread
        messages={controller.state.messages}
        isAssistantTyping={controller.isUploading}
        actions={actions}
      />
    </ChatLayout>
  );
}

export default function CreateVideoPage() {
  const apiUrl = getOrderApiUrl();
  return (
    <Suspense fallback={null}>{apiUrl ? <OrderContent apiUrl={apiUrl} /> : <LegacyDemoContent />}</Suspense>
  );
}
