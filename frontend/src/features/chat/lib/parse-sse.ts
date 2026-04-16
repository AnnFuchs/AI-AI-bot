import type { SSEEvent } from "@/entities";

type ParsedPayload = Record<string, unknown>;

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

function isObject(payload: unknown): payload is ParsedPayload {
  return Boolean(payload) && typeof payload === "object" && !Array.isArray(payload);
}

function readString(payload: ParsedPayload, keys: string[]) {
  for (const key of keys) {
    const value = payload[key];

    if (typeof value === "string") {
      return value;
    }
  }

  return undefined;
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
  const payloadObject = isObject(payload) ? payload : null;
  const eventType =
    eventName === "message" && payloadObject && typeof payloadObject.type === "string"
      ? payloadObject.type
      : eventName;

  if (eventType === "token") {
    if (typeof payload === "string") {
      return { type: "token", token: payload };
    }

    if (payloadObject) {
      return {
        type: "token",
        token: readString(payloadObject, ["token", "content", "delta", "text"]) ?? "",
      };
    }

    return { type: "token", token: "" };
  }

  if (eventType === "done") {
    if (payloadObject) {
      return {
        type: "done",
        conversationId: readString(payloadObject, ["conversationId", "conversation_id"]),
      };
    }

    return { type: "done" };
  }

  if (eventType === "error") {
    if (payloadObject) {
      return {
        type: "error",
        message:
          readString(payloadObject, ["message", "detail"]) ??
          "Поток чата завершился с ошибкой.",
      };
    }

    return { type: "error", message: "Поток чата завершился с ошибкой." };
  }

  if (eventType === "metadata" && payloadObject) {
    return { type: "metadata", data: payloadObject };
  }

  return null;
}
