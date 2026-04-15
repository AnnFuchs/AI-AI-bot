import type { SSEEvent } from "@/entities";

function parseData(data: string) {
  if (!data) {
    return {};
  }

  try {
    return JSON.parse(data) as unknown;
  } catch {
    return data;
  }
}

export function parseSSEFrame(frame: string): SSEEvent | null {
  const lines = frame.split(/\r?\n/);
  let eventName = "message";
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventName = line.slice("event:".length).trim();
      continue;
    }

    if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trim());
    }
  }

  const payload = parseData(dataLines.join("\n"));

  if (eventName === "token") {
    if (typeof payload === "string") {
      return { type: "token", token: payload };
    }

    if (
      payload &&
      typeof payload === "object" &&
      "token" in payload &&
      typeof payload.token === "string"
    ) {
      return { type: "token", token: payload.token };
    }

    return { type: "token", token: "" };
  }

  if (eventName === "done") {
    if (
      payload &&
      typeof payload === "object" &&
      "conversationId" in payload &&
      typeof payload.conversationId === "string"
    ) {
      return { type: "done", conversationId: payload.conversationId };
    }

    return { type: "done" };
  }

  if (eventName === "error") {
    if (
      payload &&
      typeof payload === "object" &&
      "message" in payload &&
      typeof payload.message === "string"
    ) {
      return { type: "error", message: payload.message };
    }

    return { type: "error", message: "Поток чата завершился с ошибкой." };
  }

  if (eventName === "metadata" && payload && typeof payload === "object") {
    return { type: "metadata", data: payload as Record<string, unknown> };
  }

  return null;
}
