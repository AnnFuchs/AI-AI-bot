import { apiClient } from "@/api/client";
import type { ChatRequest } from "@/entities";

export function streamChat(request: ChatRequest, signal?: AbortSignal) {
  return apiClient.stream<ChatRequest>("/chat/stream", {
    method: "POST",
    body: request,
    signal,
  });
}
