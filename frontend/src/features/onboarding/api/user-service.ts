import { apiClient } from "@/api/client";
import type { UserInfo, UserUpdate } from "@/entities";

export function updateCurrentUser(request: UserUpdate) {
  return apiClient.request<UserInfo, UserUpdate>("/users/me", {
    method: "PATCH",
    body: request,
  });
}
