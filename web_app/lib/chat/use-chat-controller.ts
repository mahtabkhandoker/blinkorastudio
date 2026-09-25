"use client";

import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import type { useTranslations } from "next-intl";
import { chatReducer, createInitialChatState } from "./reducer";
import { generateId } from "./id";
import {
  analyzeImageFile,
  isHardRejection,
  warningMessageKey,
} from "./image-analysis";
import { nextMissingField, parseCreativeInput } from "./parse-input";
import { runMockGeneration } from "./mock-generation";
import { loadConversation, saveConversation } from "./conversation-store";
import type {
  ChatMessage,
  CreativeInput,
  MissingField,
  QuickReplyOption,
  SupportedStyle,
  UploadedAsset,
} from "./types";
import { usePackage } from "@/lib/package/package-context";
import {
  fromBackendCreativeInput,
  getChatApiUrl,
  mapMissingField,
  sendChatMessage,
  type ChatMessageResponse,
} from "@/lib/api/chat";

type ChatTranslator = ReturnType<typeof useTranslations>;

const STYLE_OPTIONS: SupportedStyle[] = ["premium", "festive", "minimal", "energetic", "elegant"];

function now() {
  return Date.now();
}

function textMessage(role: ChatMessage["role"], text: string): ChatMessage {
  return { id: generateId("msg"), createdAt: now(), role, kind: "text", text };
}

export function useChatController(t: ChatTranslator, conversationId: string, initialTitle: string) {
  const [state, dispatch] = useReducer(
    chatReducer,
    undefined,
    () => loadConversation(conversationId) ?? createInitialChatState(conversationId, initialTitle),
  );
  const { pkg, hasQuota, consumeCredit, refundCredit } = usePackage();
  const [isUploading, setIsUploading] = useState(false);
  const generationHandleRef = useRef<{ cancel: () => void } | null>(null);
  const initializedRef = useRef(false);

  // Keep the conversation title in sync once we learn the business/campaign
  // name, so the dashboard and sidebar stop showing "New Video".
  useEffect(() => {
    const { businessName, campaignType } = state.creativeInput;
    if (!businessName && !campaignType) return;
    const nextTitle = businessName && campaignType
      ? `${businessName} — ${campaignType}`
      : businessName || campaignType || state.title;
    if (nextTitle !== state.title) {
      dispatch({ type: "SET_TITLE", payload: nextTitle });
    }
  }, [state.creativeInput, state.title]);

  // Persist on every change (mocks `POST /api/conversations/{id}`).
  useEffect(() => {
    saveConversation(state);
  }, [state]);

  useEffect(() => {
    return () => generationHandleRef.current?.cancel();
  }, []);

  const say = useCallback((text: string) => {
    dispatch({ type: "ADD_MESSAGE", payload: textMessage("assistant", text) });
  }, []);

  const askField = useCallback(
    (field: MissingField) => {
      dispatch({ type: "SET_PENDING_FIELD", payload: field });
      let text = "";
      let quickReplies: QuickReplyOption[] | undefined;

      switch (field) {
        case "intent":
          text = t("questions.intent");
          break;
        case "assets":
          text = t("questions.assets");
          dispatch({ type: "SET_STAGE", payload: "ASSET_UPLOAD" });
          break;
        case "campaignType":
          text = t("questions.campaign");
          break;
        case "style":
          text = t("questions.style");
          quickReplies = STYLE_OPTIONS.map((s) => ({
            id: s,
            label: t(`quickReplies.${s}`),
          }));
          break;
        case "duration":
          text = t("questions.duration");
          quickReplies = [10, 15, 20, 30].map((s) => ({
            id: String(s),
            label: t("quickReplies.seconds", { count: s }),
          }));
          break;
        case "platform":
          text = t("questions.platform");
          quickReplies = [
            { id: "facebook_instagram", label: t("quickReplies.facebookInstagram") },
            { id: "tiktok_reels", label: t("quickReplies.tiktokReels") },
            { id: "youtube", label: t("quickReplies.youtube") },
          ];
          break;
      }

      dispatch({
        type: "ADD_MESSAGE",
        payload: {
          id: generateId("msg"),
          createdAt: now(),
          role: "assistant",
          kind: "question",
          text,
          quickReplies,
          allowsFreeText: true,
          field,
        },
      });
    },
    [t],
  );

  const showBrief = useCallback(
    (input: CreativeInput, assetCount: number) => {
      dispatch({ type: "SET_STAGE", payload: "BRIEF_REVIEW" });
      say(t("brief.reviewIntro"));
      dispatch({
        type: "ADD_MESSAGE",
        payload: {
          id: generateId("msg"),
          createdAt: now(),
          role: "assistant",
          kind: "creative-brief",
          input,
          assetCount,
          confirmed: false,
        },
      });
    },
    [say, t],
  );

  const showPackageCheck = useCallback(() => {
    dispatch({ type: "SET_STAGE", payload: "PACKAGE_CHECK" });
    dispatch({
      type: "ADD_MESSAGE",
      payload: {
        id: generateId("msg"),
        createdAt: now(),
        role: "assistant",
        kind: "pricing",
        hasQuota,
        planName: pkg?.planName,
        videosRemaining: pkg?.videosRemaining,
      },
    });
  }, [hasQuota, pkg]);

  /** Core routing logic — mirrors the spec's suggested flow pseudocode. */
  const continueFlow = useCallback(
    (input: CreativeInput, assets: UploadedAsset[], briefConfirmed: boolean) => {
      const missing = nextMissingField(input);

      if (missing === "intent") {
        askField("intent");
        return;
      }

      const acceptedAssets = assets.filter((a) => a.status === "VALID" || a.status === "WARNING");
      if (acceptedAssets.length === 0) {
        askField("assets");
        return;
      }

      const pendingValidation = assets.some((a) => a.status === "UPLOADING" || a.status === "PROCESSING");
      if (pendingValidation) return; // wait silently; validation messages handle UI feedback

      if (missing) {
        askField(missing);
        return;
      }

      if (!briefConfirmed) {
        showBrief(input, acceptedAssets.length);
        return;
      }

      showPackageCheck();
    },
    [askField, showBrief, showPackageCheck],
  );

  /**
   * Renders whatever the chatbot backend decided (stage, missing field,
   * asset requirement, brief-readiness) — this function never makes those
   * decisions itself, it only reflects them in the UI. The backend's own
   * `reply` text and `quick_replies` are used verbatim (already localized,
   * already deterministic) instead of the local `askField`/`t(...)`
   * templates, so the two engines never show mismatched copy.
   */
  const applyRemoteResponse = useCallback(
    (response: ChatMessageResponse) => {
      const mappedInput = fromBackendCreativeInput(response.creative_input);
      dispatch({ type: "UPDATE_CREATIVE_INPUT", payload: mappedInput });
      dispatch({ type: "SET_STAGE", payload: response.stage });

      if (response.missing_field) {
        const field = mapMissingField(response.missing_field);
        dispatch({ type: "SET_PENDING_FIELD", payload: field });
        dispatch({
          type: "ADD_MESSAGE",
          payload: {
            id: generateId("msg"),
            createdAt: now(),
            role: "assistant",
            kind: "question",
            text: response.reply,
            quickReplies: response.quick_replies.map((label) => ({ id: label, label })),
            allowsFreeText: true,
            field,
          },
        });
        return;
      }

      if (response.needs_assets) {
        dispatch({ type: "SET_PENDING_FIELD", payload: "assets" });
        dispatch({ type: "ADD_MESSAGE", payload: textMessage("assistant", response.reply) });
        return;
      }

      if (response.brief_ready) {
        dispatch({ type: "SET_PENDING_FIELD", payload: undefined });
        say(response.reply);
        const merged = { ...state.creativeInput, ...mappedInput };
        const acceptedAssets = state.assets.filter((a) => a.status === "VALID" || a.status === "WARNING");
        showBrief(merged, acceptedAssets.length);
      }
    },
    [say, showBrief, state.creativeInput, state.assets],
  );

  /** Backend-mode turn: talks to the chatbot backend and renders its
   * decision. Returns `true` on success, `false` on any failure so the
   * caller can fall back to the local/mock engine transparently. */
  const runRemoteTurn = useCallback(
    async (message: string) => {
      const apiUrl = getChatApiUrl();
      if (!apiUrl) return false;
      try {
        dispatch({ type: "SET_TYPING", payload: true });
        const response = await sendChatMessage({
          apiUrl,
          conversationId: state.conversationId,
          message,
          requestId: generateId("req"),
          stage: state.stage,
          creativeInput: state.creativeInput,
          assets: state.assets,
          briefConfirmed: state.briefConfirmed,
        });
        applyRemoteResponse(response);
        return true;
      } catch (error) {
        // Network error, timeout, or non-2xx from the backend — degrade to
        // the local mock engine rather than breaking the conversation.
        console.warn("[chat] backend unavailable, using local engine for this turn", error);
        return false;
      } finally {
        dispatch({ type: "SET_TYPING", payload: false });
      }
    },
    [state.conversationId, state.stage, state.creativeInput, state.assets, state.briefConfirmed, applyRemoteResponse],
  );

  // ---- Welcome ------------------------------------------------------------
  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;
    if (state.messages.length > 0) return; // resumed conversation

    dispatch({
      type: "ADD_MESSAGE",
      payload: textMessage("assistant", t("welcomeTitle")),
    });
    dispatch({
      type: "ADD_MESSAGE",
      payload: {
        id: generateId("msg"),
        createdAt: now(),
        role: "assistant",
        kind: "question",
        text: t("welcomeBody"),
        allowsFreeText: true,
        field: "suggestion",
        quickReplies: [
          { id: "product_promo", label: t("suggestions.productPromo") },
          { id: "eid_campaign", label: t("suggestions.eidCampaign") },
          { id: "restaurant_offer", label: t("suggestions.restaurantOffer") },
          { id: "business_ad", label: t("suggestions.businessAd") },
        ],
      },
    });
    dispatch({ type: "SET_STAGE", payload: "INTENT" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- User text ------------------------------------------------------------
  const sendText = useCallback(
    (rawText: string) => {
      const text = rawText.trim();
      if (!text) return;
      dispatch({ type: "ADD_MESSAGE", payload: textMessage("user", text) });

      const extracted = parseCreativeInput(text);

      if (state.stage === "BRIEF_REVIEW" && !state.briefConfirmed) {
        // Treat as an edit instruction against the existing brief.
        const nextInput = applyEditHeuristics(state.creativeInput, text, extracted);
        dispatch({ type: "UPDATE_CREATIVE_INPUT", payload: nextInput });
        say(t("revision.planUpdated"));
        showBrief({ ...state.creativeInput, ...nextInput }, state.assets.length);
        return;
      }

      if (state.stage === "RESULT" || state.stage === "REVISION") {
        const nextInput = applyEditHeuristics(state.creativeInput, text, extracted);
        dispatch({ type: "UPDATE_CREATIVE_INPUT", payload: nextInput });
        dispatch({ type: "SET_STAGE", payload: "REVISION" });
        say(t("revision.willUseCredit"));
        const merged = { ...state.creativeInput, ...nextInput };
        showBrief(merged, state.assets.length);
        return;
      }

      if (getChatApiUrl()) {
        void runRemoteTurn(text).then((handled) => {
          if (handled) return;
          // Backend call failed — replay this turn through the local engine
          // so the user never sees a stall.
          const mergedInput = { ...state.creativeInput, ...extracted };
          dispatch({ type: "UPDATE_CREATIVE_INPUT", payload: extracted });
          continueFlow(mergedInput, state.assets, state.briefConfirmed);
        });
        return;
      }

      const mergedInput = { ...state.creativeInput, ...extracted };
      dispatch({ type: "UPDATE_CREATIVE_INPUT", payload: extracted });
      continueFlow(mergedInput, state.assets, state.briefConfirmed);
    },
    [state.stage, state.briefConfirmed, state.creativeInput, state.assets, continueFlow, say, showBrief, t, runRemoteTurn],
  );

  // ---- Quick replies --------------------------------------------------------

  /** Local/mock quick-reply handling — unchanged from before the backend
   * integration, and used both when the backend is disabled and as the
   * fallback when a backend call fails. */
  const sendQuickReplyLocal = useCallback(
    (field: MissingField | "suggestion", optionId: string, label: string) => {
      if (field === "suggestion") {
        const extracted = parseCreativeInput(label);
        const mergedInput = { ...state.creativeInput, ...extracted, campaignType: extracted.campaignType ?? label };
        dispatch({ type: "UPDATE_CREATIVE_INPUT", payload: { campaignType: mergedInput.campaignType, ...extracted } });
        continueFlow(mergedInput, state.assets, state.briefConfirmed);
        return;
      }

      let patch: Partial<CreativeInput> = {};
      switch (field) {
        case "style":
          patch = { style: [optionId as SupportedStyle] };
          break;
        case "duration":
          patch = { duration: parseInt(optionId, 10) };
          break;
        case "platform": {
          const aspect =
            optionId === "facebook_instagram" ? "1:1" : optionId === "tiktok_reels" ? "9:16" : "16:9";
          patch = { platform: optionId as CreativeInput["platform"], aspectRatio: aspect };
          break;
        }
        case "campaignType":
          patch = { campaignType: label };
          break;
        default:
          break;
      }

      const mergedInput = { ...state.creativeInput, ...patch };
      dispatch({ type: "UPDATE_CREATIVE_INPUT", payload: patch });
      continueFlow(mergedInput, state.assets, state.briefConfirmed);
    },
    [state.creativeInput, state.assets, state.briefConfirmed, continueFlow],
  );

  const sendQuickReply = useCallback(
    (field: MissingField | "suggestion", optionId: string, label: string) => {
      dispatch({ type: "ADD_MESSAGE", payload: textMessage("user", label) });

      if (getChatApiUrl()) {
        // The backend re-extracts from plain text, so every quick reply —
        // including the welcome-screen suggestions — is just replayed as
        // the message it displays. This keeps one extraction path
        // (rule_based_extract / the real LLM) instead of duplicating the
        // option->field mapping below on the server too.
        void runRemoteTurn(label).then((handled) => {
          if (handled) return;
          sendQuickReplyLocal(field, optionId, label);
        });
        return;
      }

      sendQuickReplyLocal(field, optionId, label);
    },
    [runRemoteTurn, sendQuickReplyLocal],
  );

  // ---- Asset upload + validation ---------------------------------------------
  const uploadFiles = useCallback(
    async (files: FileList | File[]) => {
      const fileArray = Array.from(files);
      if (fileArray.length === 0) return;
      setIsUploading(true);

      const newAssets: UploadedAsset[] = fileArray.map((file) => ({
        id: generateId("asset"),
        name: file.name,
        type: "image",
        url: URL.createObjectURL(file),
        status: "UPLOADING",
        sizeBytes: file.size,
      }));

      dispatch({
        type: "ADD_MESSAGE",
        payload: { id: generateId("msg"), createdAt: now(), role: "user", kind: "asset", assets: newAssets },
      });
      newAssets.forEach((asset) => dispatch({ type: "ADD_ASSET", payload: asset }));
      if (state.stage === "ASSET_UPLOAD" || state.stage === "INTENT") {
        dispatch({ type: "SET_STAGE", payload: "ASSET_VALIDATION" });
      }

      for (let i = 0; i < fileArray.length; i += 1) {
        const file = fileArray[i];
        const asset = newAssets[i];
        dispatch({ type: "UPDATE_ASSET", payload: { ...asset, status: "PROCESSING" } });

        // Small delay so the "checking image..." affordance is perceptible.
        await new Promise((resolve) => setTimeout(resolve, 500));
        const analysis = await analyzeImageFile(file);

        const updated: UploadedAsset = {
          ...asset,
          width: analysis.width,
          height: analysis.height,
          status: analysis.warningCode
            ? isHardRejection(analysis.warningCode)
              ? "REJECTED"
              : "WARNING"
            : "VALID",
          warningCode: analysis.warningCode,
          warningMessage: analysis.warningCode ? t(warningMessageKey(analysis.warningCode)) : undefined,
        };

        dispatch({ type: "UPDATE_ASSET", payload: updated });
        dispatch({
          type: "ADD_MESSAGE",
          payload: {
            id: generateId("msg"),
            createdAt: now(),
            role: "assistant",
            kind: "validation",
            asset: updated,
          },
        });
      }

      setIsUploading(false);
    },
    [state.stage, t],
  );

  const replaceAsset = useCallback((assetId: string) => {
    dispatch({ type: "REMOVE_ASSET", payload: { id: assetId } });
  }, []);

  const acceptAssetAnyway = useCallback(
    (assetId: string) => {
      const asset = state.assets.find((a) => a.id === assetId);
      if (!asset) return;
      const accepted: UploadedAsset = { ...asset, status: "VALID" };
      dispatch({ type: "UPDATE_ASSET", payload: accepted });
      continueFlow(state.creativeInput, state.assets.map((a) => (a.id === assetId ? accepted : a)), state.briefConfirmed);
    },
    [state.assets, state.creativeInput, state.briefConfirmed, continueFlow],
  );

  // Advance the flow automatically whenever an accepted asset appears
  // (covers "user replaces image" -> flow should continue).
  useEffect(() => {
    if (state.stage !== "ASSET_VALIDATION") return;
    const stillPending = state.assets.some((a) => a.status === "UPLOADING" || a.status === "PROCESSING");
    if (stillPending) return;
    const accepted = state.assets.filter((a) => a.status === "VALID" || a.status === "WARNING");
    if (accepted.length > 0) {
      continueFlow(state.creativeInput, state.assets, state.briefConfirmed);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.assets, state.stage]);

  // ---- Brief confirmation -----------------------------------------------------
  const confirmBrief = useCallback(() => {
    dispatch({ type: "SET_BRIEF_CONFIRMED", payload: true });
    showPackageCheck();
  }, [showPackageCheck]);

  const editBrief = useCallback(() => {
    say(t("brief.reviewIntro"));
    dispatch({
      type: "ADD_MESSAGE",
      payload: {
        id: generateId("msg"),
        createdAt: now(),
        role: "assistant",
        kind: "question",
        text: "কী পরিবর্তন করতে চান? / What would you like to change?",
        allowsFreeText: true,
      },
    });
  }, [say, t]);

  // ---- Generation -----------------------------------------------------------
  const startGeneration = useCallback(
    (isRevision = false) => {
      if (state.generationClickLock) return; // prevents duplicate paid generations
      if (!hasQuota) {
        showPackageCheck();
        return;
      }

      dispatch({ type: "LOCK_GENERATION_CLICK", payload: true });
      consumeCredit();

      const generationId = generateId("gen");
      dispatch({
        type: "START_GENERATION",
        payload: { id: generationId, status: "QUEUED", progress: 0, isRevision },
      });

      const statusMessageId = generateId("msg");
      dispatch({
        type: "ADD_MESSAGE",
        payload: {
          id: statusMessageId,
          createdAt: now(),
          role: "assistant",
          kind: "generation-status",
          generation: { id: generationId, status: "QUEUED", progress: 0, isRevision },
        },
      });

      generationHandleRef.current = runMockGeneration({
        onUpdate: ({ status, progress }) => {
          dispatch({ type: "UPDATE_GENERATION", payload: { status, progress } });
          dispatch({
            type: "REPLACE_MESSAGE",
            payload: {
              id: statusMessageId,
              message: {
                id: statusMessageId,
                createdAt: now(),
                role: "assistant",
                kind: "generation-status",
                generation: { id: generationId, status, progress, isRevision },
              },
            },
          });
        },
        onComplete: (videoUrl) => {
          dispatch({ type: "UPDATE_GENERATION", payload: { status: "COMPLETED", progress: 100, videoUrl } });
          dispatch({ type: "SET_STAGE", payload: "RESULT" });
          dispatch({ type: "LOCK_GENERATION_CLICK", payload: false });
          dispatch({
            type: "ADD_MESSAGE",
            payload: {
              id: generateId("msg"),
              createdAt: now(),
              role: "assistant",
              kind: "video-result",
              generation: {
                id: generationId,
                status: "COMPLETED",
                progress: 100,
                videoUrl,
                isRevision,
                versionLabel: isRevision ? "Revised version" : undefined,
              },
              input: state.creativeInput,
            },
          });
        },
        onError: (message) => {
          refundCredit();
          dispatch({ type: "UPDATE_GENERATION", payload: { status: "FAILED", error: message } });
          dispatch({ type: "SET_STAGE", payload: "FAILED" });
          dispatch({ type: "LOCK_GENERATION_CLICK", payload: false });
          dispatch({
            type: "ADD_MESSAGE",
            payload: {
              id: generateId("msg"),
              createdAt: now(),
              role: "assistant",
              kind: "error",
              text: t("errors.generationFailed"),
              retryable: true,
            },
          });
        },
      });
    },
    [state.generationClickLock, state.creativeInput, hasQuota, consumeCredit, refundCredit, showPackageCheck, t],
  );

  const retryGeneration = useCallback(() => {
    dispatch({ type: "SET_STAGE", payload: "GENERATION_CONFIRMATION" });
    startGeneration(false);
  }, [startGeneration]);

  const requestRevision = useCallback(
    (label: string, patch: Partial<CreativeInput> = {}) => {
      dispatch({ type: "ADD_MESSAGE", payload: textMessage("user", label) });
      const merged = { ...state.creativeInput, ...patch };
      dispatch({ type: "UPDATE_CREATIVE_INPUT", payload: patch });
      dispatch({ type: "SET_STAGE", payload: "REVISION" });
      say(t("revision.willUseCredit"));
      showBrief(merged, state.assets.length);
    },
    [state.creativeInput, state.assets.length, say, showBrief, t],
  );

  return {
    state,
    isUploading,
    hasQuota,
    pkg,
    sendText,
    sendQuickReply,
    uploadFiles,
    replaceAsset,
    acceptAssetAnyway,
    confirmBrief,
    editBrief,
    startGeneration,
    retryGeneration,
    requestRevision,
  };
}

/** Handles common natural-language edit phrases against an existing brief. */
function applyEditHeuristics(
  current: CreativeInput,
  text: string,
  extracted: Partial<CreativeInput>,
): Partial<CreativeInput> {
  const lower = text.toLowerCase();
  const patch: Partial<CreativeInput> = { ...extracted };

  if (/more premium|aro premium|আরও প্রিমিয়াম/.test(lower)) {
    patch.style = Array.from(new Set([...(current.style ?? []), "premium" as SupportedStyle]));
  }
  if (/no voice.?over|voiceover.*na|ভয়েসওভার.*না/.test(lower)) {
    patch.voiceover = false;
  }
  if (/no caption|caption bad|ক্যাপশন বাদ/.test(lower)) {
    patch.captions = false;
  }
  const durationMatch = lower.match(/(\d{1,2})\s*sec/);
  if (durationMatch) {
    patch.duration = parseInt(durationMatch[1], 10);
  }
  if (/shorter|choto|ছোট/.test(lower) && current.duration) {
    patch.duration = Math.max(10, current.duration - 5);
  }

  return patch;
}
