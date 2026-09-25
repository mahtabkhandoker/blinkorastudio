"use client";

import { useTranslations } from "next-intl";
import type { ChatMessage, CreativeInput, QuickReplyOption } from "@/lib/chat/types";
import { UserMessage } from "./UserMessage";
import { AssistantMessage } from "./AssistantMessage";
import { QuickReplies } from "./QuickReplies";
import { AssetCard } from "./cards/AssetCard";
import { AssetValidationCard } from "./cards/AssetValidationCard";
import { CreativeBriefCard } from "./cards/CreativeBriefCard";
import { PackageCheckCard } from "./cards/PackageCheckCard";
import { GenerationStatusCard } from "./cards/GenerationStatusCard";
import { VideoResultCard } from "./cards/VideoResultCard";
import { ErrorCard } from "./cards/ErrorCard";

export type ChatMessageActions = {
  conversationId: string;
  onQuickReply: (messageId: string, field: string, optionId: string, label: string) => void;
  onReplaceAsset: (assetId: string) => void;
  onAcceptAssetAnyway: (assetId: string) => void;
  onEditBrief: () => void;
  onConfirmBrief: () => void;
  onConfirmGeneration: () => void;
  onRetryGeneration: () => void;
  onFollowUp: (label: string, patch?: Partial<CreativeInput>) => void;
  answeredQuickReplyIds: Set<string>;
};

export function ChatMessageItem({
  message,
  actions,
}: {
  message: ChatMessage;
  actions: ChatMessageActions;
}) {
  const t = useTranslations("chat");

  if (message.role === "user") {
    if (message.kind === "text") {
      return <UserMessage>{message.text}</UserMessage>;
    }
    if (message.kind === "asset") {
      return (
        <div className="flex justify-end">
          <div className="flex max-w-[85%] gap-2 overflow-x-auto pb-1">
            {message.assets.map((asset) => (
              <AssetCard key={asset.id} asset={asset} />
            ))}
          </div>
        </div>
      );
    }
    return null;
  }

  switch (message.kind) {
    case "text":
      return <AssistantMessage>{message.text}</AssistantMessage>;

    case "question": {
      const alreadyAnswered = actions.answeredQuickReplyIds.has(message.id);
      return (
        <AssistantMessage>
          <p>{message.text}</p>
          {message.quickReplies && (
            <QuickReplies
              disabled={alreadyAnswered}
              options={message.quickReplies}
              onSelect={(option: QuickReplyOption) =>
                actions.onQuickReply(message.id, message.field ?? "suggestion", option.id, option.label)
              }
            />
          )}
        </AssistantMessage>
      );
    }

    case "validation":
      return (
        <AssistantMessage bare>
          <AssetValidationCard
            asset={message.asset}
            onReplace={() => actions.onReplaceAsset(message.asset.id)}
            onContinueAnyway={() => actions.onAcceptAssetAnyway(message.asset.id)}
          />
        </AssistantMessage>
      );

    case "creative-brief":
      return (
        <AssistantMessage bare>
          <CreativeBriefCard
            input={message.input}
            assetCount={message.assetCount}
            confirmed={message.confirmed}
            onEdit={actions.onEditBrief}
            onConfirm={actions.onConfirmBrief}
          />
        </AssistantMessage>
      );

    case "pricing":
      return (
        <AssistantMessage bare>
          <PackageCheckCard
            hasQuota={message.hasQuota}
            planName={message.planName}
            videosRemaining={message.videosRemaining}
            conversationId={actions.conversationId}
            onConfirm={actions.onConfirmGeneration}
          />
        </AssistantMessage>
      );

    case "generation-status":
      return (
        <AssistantMessage bare>
          <GenerationStatusCard generation={message.generation} />
        </AssistantMessage>
      );

    case "video-result":
      return (
        <AssistantMessage bare>
          <VideoResultCard
            generation={message.generation}
            input={message.input}
            onFollowUp={actions.onFollowUp}
            onRegenerate={() => actions.onFollowUp(t("regenerate"))}
            onMakeChanges={actions.onEditBrief}
          />
        </AssistantMessage>
      );

    case "error":
      return (
        <AssistantMessage bare>
          <ErrorCard text={message.text} retryable={message.retryable} onRetry={actions.onRetryGeneration} />
        </AssistantMessage>
      );

    default:
      return null;
  }
}
