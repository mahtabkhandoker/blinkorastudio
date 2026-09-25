import type { ChatAction, ChatState } from "./types";

export function createInitialChatState(conversationId: string, title: string): ChatState {
  return {
    conversationId,
    title,
    stage: "WELCOME",
    messages: [],
    creativeInput: {},
    assets: [],
    generation: undefined,
    pendingQuestionField: "intent",
    briefConfirmed: false,
    isAssistantTyping: false,
    generationClickLock: false,
  };
}

export function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case "ADD_MESSAGE":
      return { ...state, messages: [...state.messages, action.payload] };

    case "REPLACE_MESSAGE":
      return {
        ...state,
        messages: state.messages.map((m) =>
          m.id === action.payload.id ? action.payload.message : m,
        ),
      };

    case "SET_STAGE":
      return { ...state, stage: action.payload };

    case "ADD_ASSET":
      return { ...state, assets: [...state.assets, action.payload] };

    case "UPDATE_ASSET":
      return {
        ...state,
        assets: state.assets.map((a) =>
          a.id === action.payload.id ? action.payload : a,
        ),
      };

    case "REMOVE_ASSET":
      return {
        ...state,
        assets: state.assets.filter((a) => a.id !== action.payload.id),
      };

    case "UPDATE_CREATIVE_INPUT":
      return {
        ...state,
        creativeInput: { ...state.creativeInput, ...action.payload },
      };

    case "SET_PENDING_FIELD":
      return { ...state, pendingQuestionField: action.payload };

    case "SET_BRIEF_CONFIRMED":
      return { ...state, briefConfirmed: action.payload };

    case "SET_TYPING":
      return { ...state, isAssistantTyping: action.payload };

    case "START_GENERATION":
      return { ...state, generation: action.payload, stage: "GENERATING" };

    case "UPDATE_GENERATION":
      return {
        ...state,
        generation: state.generation
          ? { ...state.generation, ...action.payload }
          : { status: "QUEUED", ...action.payload },
      };

    case "SET_TITLE":
      return { ...state, title: action.payload };

    case "LOCK_GENERATION_CLICK":
      return { ...state, generationClickLock: action.payload };

    case "RESET":
      return createInitialChatState(state.conversationId, state.title);

    default:
      return state;
  }
}
