import { apiClient } from "@/api/client";
import type { AuthCredentials, AuthToken, RefreshTokenRequest, RegisterRequest } from "@/entities";

import { clearAuthToken, saveAuthToken } from "../lib/token-storage";

export async function login(request: AuthCredentials) {
  const token = await apiClient.request<AuthToken, AuthCredentials>("/auth/login", {
    method: "POST",
    body: request,
    auth: false,
  });

  saveAuthToken(token);

  return token;
}

export async function register(request: RegisterRequest) {
  await apiClient.request<void, RegisterRequest>("/users/register", {
    method: "POST",
    body: request,
    auth: false,
  });

  return login({
    login: request.phone,
    password: request.password,
  });
}

export function refreshAuth(request: RefreshTokenRequest) {
  return apiClient.request<AuthToken, RefreshTokenRequest>("/auth/refresh", {
    method: "POST",
    body: request,
    auth: false,
  });
}

export async function logout(refreshToken: string) {
  await apiClient.request<{ detail: string }, RefreshTokenRequest>("/auth/logout", {
    method: "POST",
    body: {
      refresh_token: refreshToken,
    },
  });

  clearAuthToken();
}
