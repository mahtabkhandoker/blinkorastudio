/**
 * Domain types for the chat-first video creation workflow.
 *
 * This models a controlled workflow/state machine that happens to be
 * presented conversationally — NOT a free-form chatbot. `CreationStage`
 * is the single source of truth for what the UI should render/allow next;
 * `ChatMessage` is purely a rendering log of that workflow.
 */

export type CreationStage =
  | "WELCOME"
  | "INTENT"
  | "ASSET_UPLOAD"
  | "ASSET_VALIDATION"
  | "DETAILS_COLLECTION"
  | "BRIEF_REVIEW"
  | "PACKAGE_CHECK"
  | "GENERATION_CONFIRMATION"
  | "GENERATING"
  | "QUALITY_CHECK"
  | "RESULT"
  | "REVISION"
  | "FAILED";

export type SupportedStyle =
  | "premium"
  | "festive"
  | "minimal"
  | "energetic"
  | "elegant";

export type Platform = "facebook_instagram" | "tiktok_reels" | "youtube";

export type CreativeInput = {
  businessName?: string;
  businessType?: string;
  productName?: string;
  productCategory?: string;
  campaignType?: string;
  targetAudience?: string;
  duration?: number;
  aspectRatio?: "9:16" | "1:1" | "16:9";
  platform?: Platform;
  style?: SupportedStyle[];
  language?: string;
  captions?: boolean;
  voiceover?: boolean;
  musicMood?: string;
  cta?: string;
};

export type AssetStatus = "UPLOADING" | "PROCESSING" | "VALID" | "WARNING" | "REJECTED";

export type AssetWarningCode =
  | "BLURRY"
  | "LOW_RESOLUTION"
  | "TOO_DARK"
  | "CROPPED"
  | "CORRUPT"
  | "UNSUPPORTED";

export type UploadedAsset = {
  id: string;
  name: string;
  type: "image" | "logo" | "other";
  /** Object URL for local preview only — never a persisted backend URL yet. */
  url: string;
  status: AssetStatus;
  width?: number;
  height?: number;
  sizeBytes?: number;
  warningCode?: AssetWarningCode;
  warningMessage?: string;
};

export type GenerationStageKey =
  | "QUEUED"
  | "PREPARING"
  | "GENERATING"
  | "VALIDATING"
  | "FINALIZING"
  | "COMPLETED"
  | "FAILED";

export type GenerationState = {
  id?: string;
  status: GenerationStageKey;
  progress?: number;
  videoUrl?: string;
  error?: string;
  isRevision?: boolean;
  versionLabel?: string;
};

// ---- Chat message variants -------------------------------------------------

type BaseMessage = {
  id: string;
  createdAt: number;
  role: "assistant" | "user";
};

export type TextMessage = BaseMessage & {
  kind: "text";
  text: string;
};

export type QuickReplyOption = {
  id: string;
  label: string;
};

export type QuestionMessage = BaseMessage & {
  kind: "question";
  text: string;
  quickReplies?: QuickReplyOption[];
  allowsFreeText?: boolean;
  /** Which creative-input field a quick-reply click on this message answers. */
  field?: MissingField | "suggestion";
};

export type AssetMessage = BaseMessage & {
  kind: "asset";
  assets: UploadedAsset[];
};

export type ValidationMessage = BaseMessage & {
  kind: "validation";
  asset: UploadedAsset;
};

export type CreativeBriefMessage = BaseMessage & {
  kind: "creative-brief";
  input: CreativeInput;
  assetCount: number;
  confirmed: boolean;
};

export type PricingMessage = BaseMessage & {
  kind: "pricing";
  hasQuota: boolean;
  planName?: string;
  videosRemaining?: number;
};

export type GenerationStatusMessage = BaseMessage & {
  kind: "generation-status";
  generation: GenerationState;
};

export type VideoResultMessage = BaseMessage & {
  kind: "video-result";
  generation: GenerationState;
  input: CreativeInput;
};

export type ErrorMessage = BaseMessage & {
  kind: "error";
  text: string;
  retryable?: boolean;
};

export type ChatMessage =
  | TextMessage
  | QuestionMessage
  | AssetMessage
  | ValidationMessage
  | CreativeBriefMessage
  | PricingMessage
  | GenerationStatusMessage
  | VideoResultMessage
  | ErrorMessage;

export type ConversationSummary = {
  id: string;
  title: string;
  status: "active" | "generating" | "completed" | "failed";
  updatedAt: number;
};

export type ChatState = {
  conversationId: string;
  title: string;
  stage: CreationStage;
  messages: ChatMessage[];
  creativeInput: CreativeInput;
  assets: UploadedAsset[];
  generation?: GenerationState;
  pendingQuestionField?: MissingField;
  briefConfirmed: boolean;
  isAssistantTyping: boolean;
  generationClickLock: boolean;
};

export type MissingField =
  | "intent"
  | "assets"
  | "campaignType"
  | "style"
  | "duration"
  | "platform";

export type ChatAction =
  | { type: "ADD_MESSAGE"; payload: ChatMessage }
  | { type: "REPLACE_MESSAGE"; payload: { id: string; message: ChatMessage } }
  | { type: "SET_STAGE"; payload: CreationStage }
  | { type: "ADD_ASSET"; payload: UploadedAsset }
  | { type: "UPDATE_ASSET"; payload: UploadedAsset }
  | { type: "REMOVE_ASSET"; payload: { id: string } }
  | { type: "UPDATE_CREATIVE_INPUT"; payload: Partial<CreativeInput> }
  | { type: "SET_PENDING_FIELD"; payload: MissingField | undefined }
  | { type: "SET_BRIEF_CONFIRMED"; payload: boolean }
  | { type: "SET_TYPING"; payload: boolean }
  | { type: "START_GENERATION"; payload: GenerationState }
  | { type: "UPDATE_GENERATION"; payload: Partial<GenerationState> }
  | { type: "SET_TITLE"; payload: string }
  | { type: "LOCK_GENERATION_CLICK"; payload: boolean }
  | { type: "RESET" };
