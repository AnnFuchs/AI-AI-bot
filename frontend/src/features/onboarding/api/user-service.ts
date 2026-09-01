import { apiClient } from "@/api/client";
import type { UserInfo, UserUpdate } from "@/entities";

type TimezoneUpdate = {
  timezone: string;
};

export function getCurrentUser() {
  return apiClient.request<UserInfo>("/users/me");
}

export function updateCurrentUser(request: UserUpdate) {
  return apiClient.request<UserInfo, UserUpdate>("/users/me", {
    method: "PATCH",
    body: request,
  });
}

export function syncTimezone(request: TimezoneUpdate) {
  return apiClient.request<UserInfo, TimezoneUpdate>("/users/me/timezone", {
    method: "PATCH",
    body: request,
  });
}
