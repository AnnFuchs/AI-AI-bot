import type { AuthToken } from "@/entities";

const ACCESS_TOKEN_KEY = "ai-ai.access-token";
const REFRESH_TOKEN_KEY = "ai-ai.refresh-token";
const TOKEN_TYPE_KEY = "ai-ai.token-type";

function getStorage() {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage;
}

export function getAccessToken() {
  return getStorage()?.getItem(ACCESS_TOKEN_KEY) ?? null;
}

export function getRefreshToken() {
  return getStorage()?.getItem(REFRESH_TOKEN_KEY) ?? null;
}

export function saveAuthToken(token: AuthToken) {
  const storage = getStorage();

  if (!storage) {
    return;
  }

  storage.setItem(ACCESS_TOKEN_KEY, token.access_token);
  storage.setItem(REFRESH_TOKEN_KEY, token.refresh_token);
  storage.setItem(TOKEN_TYPE_KEY, token.token_type);
}

export function clearAuthToken() {
  const storage = getStorage();

  if (!storage) {
    return;
  }

  storage.removeItem(ACCESS_TOKEN_KEY);
  storage.removeItem(REFRESH_TOKEN_KEY);
  storage.removeItem(TOKEN_TYPE_KEY);
}
