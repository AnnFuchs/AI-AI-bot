"use client";

import { useCallback, useRef, useState } from "react";

import type { ChatAction, ChatMessage, SSEEvent } from "@/entities";

import { streamChat } from "../api/chat-service";
import { STROKE_INFO_ACTION } from "../lib/chat-actions";
import { parseSSEFrame } from "../lib/parse-sse";

type StreamStatus = "idle" | "streaming" | "error";

function createId() {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
}

function createMessage(role: ChatMessage["role"], content: string): ChatMessage {
  return {
    id: createId(),
    role,
    content,
    createdAt: new Date().toISOString(),
  };
}

function createAction(action: Omit<ChatAction, "id">): ChatAction {
  return {
    id: createId(),
    ...action,
  };
}

function appendAssistantContent(message: ChatMessage, content: string): ChatMessage {
  return {
    ...message,
    content: `${message.content}${content}`,
  };
}

function appendAssistantAction(message: ChatMessage, action: Omit<ChatAction, "id">): ChatMessage {
  const actions = message.actions ?? [];
  const shouldAddStrokeInfoAction = !actions.some(
    (currentAction) => currentAction.href === STROKE_INFO_ACTION.href,
  );

  return {
    ...message,
    actions: [
      ...actions,
      createAction(action),
      ...(shouldAddStrokeInfoAction ? [createAction(STROKE_INFO_ACTION)] : []),
    ],
  };
}

export function useChatStream() {
  const sessionIdRef = useRef(createId());
  const [messages, setMessages] = useState<ChatMessage[]>([createMessage("assistant", "welcome")]);
  const [status, setStatus] = useState<StreamStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const applyEvent = useCallback((event: SSEEvent, assistantMessageId: string) => {
    if (event.type === "token" || event.type === "text") {
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantMessageId
            ? appendAssistantContent(message, event.type === "token" ? event.token : event.text)
            : message,
        ),
      );
    }

    if (event.type === "button") {
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantMessageId
            ? appendAssistantAction(message, event.button)
            : message,
        ),
      );
    }

    if (event.type === "alert") {
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantMessageId
            ? {
                ...message,
                alerts: [...(message.alerts ?? []), event.alert],
              }
            : message,
        ),
      );
    }

    if (event.type === "sources") {
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantMessageId
            ? {
                ...message,
                sources: [...(message.sources ?? []), event.sources],
              }
            : message,
        ),
      );
    }

    if (event.type === "error") {
      throw new Error(event.message);
    }
  }, []);

  const sendMessage = useCallback(
    async (message: string) => {
      const trimmedMessage = message.trim();

      if (!trimmedMessage || status === "streaming") {
        return;
      }

      abortControllerRef.current?.abort();

      const abortController = new AbortController();
      abortControllerRef.current = abortController;
      const assistantMessage = createMessage("assistant", "");

      setError(null);
      setStatus("streaming");
      setMessages((current) => [
        ...current,
        createMessage("user", trimmedMessage),
        assistantMessage,
      ]);

      try {
        const stream = await streamChat(
          { message: trimmedMessage, session_id: sessionIdRef.current },
          abortController.signal,
        );
        const reader = stream.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let done = false;

        while (!done) {
          const chunk = await reader.read();
          done = chunk.done;

          if (chunk.value) {
            buffer += decoder.decode(chunk.value, { stream: true });
          }

          const frames = buffer.split(/\r?\n\r?\n/);
          buffer = frames.pop() ?? "";

          for (const frame of frames) {
            const event = parseSSEFrame(frame);

            if (!event) {
              continue;
            }

            applyEvent(event, assistantMessage.id);

            if (event.type === "done") {
              done = true;
              break;
            }
          }
        }

        setStatus("idle");
      } catch (caughtError) {
        if (abortController.signal.aborted) {
          setStatus("idle");
          return;
        }

        setStatus("error");
        setError(
          caughtError instanceof Error
            ? caughtError.message
            : "Ай-Яй сейчас не смог ответить. Попробуйте еще раз.",
        );
      } finally {
        if (abortControllerRef.current === abortController) {
          abortControllerRef.current = null;
        }
      }
    },
    [applyEvent, status],
  );

  const stop = useCallback(() => {
    abortControllerRef.current?.abort();
    setStatus("idle");
  }, []);

  return {
    error,
    messages,
    sendMessage,
    status,
    stop,
  };
}
