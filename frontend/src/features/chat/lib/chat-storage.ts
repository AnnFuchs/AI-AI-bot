import type { ChatMessage } from "@/entities";

const CHAT_STORAGE_KEY = "stroke-buddy:chat";

type StoredChatState = {
  sessionId: string;
  messages: ChatMessage[];
};

function isBrowser() {
  return typeof window !== "undefined";
}

function isStoredChatState(value: unknown): value is StoredChatState {
  if (!value || typeof value !== "object") {
    return false;
  }

  const state = value as Partial<StoredChatState>;

  return (
    typeof state.sessionId === "string" &&
    state.sessionId.length > 0 &&
    Array.isArray(state.messages)
  );
}

export function loadStoredChatState() {
  if (!isBrowser()) {
    return null;
  }

  const rawState = window.localStorage.getItem(CHAT_STORAGE_KEY);

  if (!rawState) {
    return null;
  }

  try {
    const parsedState = JSON.parse(rawState);

    return isStoredChatState(parsedState) ? parsedState : null;
  } catch {
    return null;
  }
}

export function saveStoredChatState(state: StoredChatState) {
  if (!isBrowser()) {
    return;
  }

  window.localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(state));
}
