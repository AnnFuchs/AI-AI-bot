import type { SSEEvent } from "@/entities";

type ParsedPayload = Record<string, unknown>;

const URL_PATTERN = /https?:\/\/\S+/;
const EMPTY_TEXT_VALUES = new Set(["", "none", "null", "undefined"]);

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

function normalizeOptionalString(value: string | undefined) {
  if (value === undefined) {
    return undefined;
  }

  const trimmedValue = value.trim();

  return EMPTY_TEXT_VALUES.has(trimmedValue.toLowerCase()) ? undefined : trimmedValue;
}

function readOptionalString(payload: ParsedPayload, keys: string[]) {
  return normalizeOptionalString(readString(payload, keys));
}

function readEventPayload(payload: ParsedPayload | null) {
  if (!payload) {
    return null;
  }

  return isObject(payload.payload) ? payload.payload : payload;
}

function readButtonPayload(payload: ParsedPayload) {
  if (isObject(payload.button)) {
    return payload.button;
  }

  if (isObject(payload.payload)) {
    return payload.payload;
  }

  return payload;
}

function readObjectList(payload: ParsedPayload, key: string) {
  const value = payload[key];

  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter(isObject);
}

function parseFormattedSource(source: string) {
  const trimmedSource = normalizeOptionalString(source);

  if (!trimmedSource) {
    return null;
  }

  const url = trimmedSource.match(URL_PATTERN)?.[0];
  const title = normalizeOptionalString(
    (url ? trimmedSource.replace(url, "") : trimmedSource).replace(
      /(?:\s+(?:none|null|undefined))+$/i,
      "",
    ),
  );

  return {
    source: title ?? trimmedSource,
    title: title ?? trimmedSource,
    url,
  };
}

function readSources(payload: ParsedPayload) {
  const value = payload.sources;

  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((source) => {
      return typeof source === "string" ? parseFormattedSource(source) : null;
    })
    .filter((source) => source !== null);
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
          readString(eventPayload ?? payloadObject, ["token", "content", "delta", "text"]) ?? "",
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
      const buttonPayload = readButtonPayload(payloadObject);

      return {
        type: "button",
        button: {
          label: readString(buttonPayload, ["label", "title", "text"]) ?? "Открыть памятку",
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
    const sources = readSources(eventPayload);

    return {
      type: "sources",
      sources: {
        confidence_label: readOptionalString(eventPayload, ["confidence_label"]),
        sources,
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
          readString(payloadObject, ["message", "detail"]) ?? "Поток чата завершился с ошибкой.",
      };
    }

    return { type: "error", message: "Поток чата завершился с ошибкой." };
  }

  if (eventType === "metadata" && payloadObject) {
    return { type: "metadata", data: payloadObject };
  }

  return null;
}
