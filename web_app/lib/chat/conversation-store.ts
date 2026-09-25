import type { ChatState, ConversationSummary, CreationStage } from "./types";

/**
 * MOCK persistence layer — localStorage stands in for
 * `GET/POST /api/conversations`. Keeping this behind a small set of
 * functions (rather than scattering localStorage calls through components)
 * means swapping in real API calls later only touches this file.
 */

const INDEX_KEY = "blinkora.chat.index";
const STATE_KEY_PREFIX = "blinkora.chat.state.";

function stageToStatus(stage: CreationStage): ConversationSummary["status"] {
  if (stage === "FAILED") return "failed";
  if (stage === "RESULT") return "completed";
  if (stage === "GENERATING" || stage === "QUALITY_CHECK") return "generating";
  return "active";
}

export function listConversations(): ConversationSummary[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(INDEX_KEY);
    const list = raw ? (JSON.parse(raw) as ConversationSummary[]) : [];
    return list.sort((a, b) => b.updatedAt - a.updatedAt);
  } catch {
    return [];
  }
}

export function loadConversation(id: string): ChatState | undefined {
  if (typeof window === "undefined") return undefined;
  try {
    const raw = window.localStorage.getItem(STATE_KEY_PREFIX + id);
    return raw ? (JSON.parse(raw) as ChatState) : undefined;
  } catch {
    return undefined;
  }
}

export function saveConversation(state: ChatState): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STATE_KEY_PREFIX + state.conversationId, JSON.stringify(state));

    const index = listConversations().filter((c) => c.id !== state.conversationId);
    index.push({
      id: state.conversationId,
      title: state.title,
      status: stageToStatus(state.stage),
      updatedAt: Date.now(),
    });
    window.localStorage.setItem(INDEX_KEY, JSON.stringify(index));
  } catch {
    // Best-effort only; local demo persistence should never break the UI.
  }
}

export function deleteConversation(id: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STATE_KEY_PREFIX + id);
  const index = listConversations().filter((c) => c.id !== id);
  window.localStorage.setItem(INDEX_KEY, JSON.stringify(index));
}
