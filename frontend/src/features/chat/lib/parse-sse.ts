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

function readNumber(payload: ParsedPayload, keys: string[]) {
  for (const key of keys) {
    const value = payload[key];

    if (typeof value === "number") {
      return value;
    }
  }

  return undefined;
}

function readBoolean(payload: ParsedPayload, keys: string[]) {
  for (const key of keys) {
    const value = payload[key];

    if (typeof value === "boolean") {
      return value;
    }
  }

  return undefined;
}

function readEventPayload(payload: ParsedPayload | null) {
  if (!payload) {
    return null;
  }

  return isObject(payload.payload) ? payload.payload : payload;
}

function readObjectList(payload: ParsedPayload, key: string) {
  const value = payload[key];

  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter(isObject);
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
  const eventPayload = readEventPayload(payloadObject);
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
        token:
          readString(eventPayload ?? payloadObject, ["token", "content", "delta", "text"]) ??
          "",
      };
    }

    return { type: "token", token: "" };
  }

  if (eventType === "text") {
    if (typeof payload === "string") {
      return { type: "text", text: payload };
    }

    if (payloadObject) {
      return {
        type: "text",
        text: readString(eventPayload ?? payloadObject, ["text", "message", "content"]) ?? "",
      };
    }

    return { type: "text", text: "" };
  }

  if (eventType === "button") {
    if (typeof payload === "string") {
      return {
        type: "button",
        button: {
          label: payload,
          href: "/learn",
        },
      };
    }

    if (payloadObject) {
      const buttonPayload = eventPayload ?? payloadObject;

      return {
        type: "button",
        button: {
          label:
            readString(buttonPayload, ["label", "title", "text"]) ??
            "Открыть памятку",
          href: readString(buttonPayload, ["href", "url", "link"]) ?? "/learn",
        },
      };
    }

    return {
      type: "button",
      button: {
        label: "Открыть памятку",
        href: "/learn",
      },
    };
  }

  if (eventType === "alert" && eventPayload) {
    const redFlags = readObjectList(eventPayload, "red_flags").map((flag) => ({
      name: readString(flag, ["name"]) ?? "",
      level: readString(flag, ["level"]) ?? "",
      description: readString(flag, ["description"]) ?? "",
      target_info: readString(flag, ["target_info", "targetInfo"]),
    }));

    return {
      type: "alert",
      alert: {
        message: readString(eventPayload, ["message", "text"]) ?? "",
        red_flags: redFlags,
      },
    };
  }

  if (eventType === "sources" && eventPayload) {
    const sources = readObjectList(eventPayload, "sources").map((source) => ({
      source: readString(source, ["source", "name"]) ?? "",
      title: readString(source, ["title"]),
      url: readString(source, ["url", "href", "link"]),
    }));

    return {
      type: "sources",
      sources: {
        confidence: readNumber(eventPayload, ["confidence"]),
        confidence_label: readString(eventPayload, [
          "confidence_label",
          "confidenceLabel",
        ]),
        sources,
        used_rag: readBoolean(eventPayload, ["used_rag", "usedRag"]),
      },
    };
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
