"use client";

import { useCallback, useRef, useState } from "react";

import type { ChatMessage, SSEEvent } from "@/entities";

import { streamChat } from "../api/chat-service";
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

export function useChatStream() {
  const sessionIdRef = useRef(createId());
  const [messages, setMessages] = useState<ChatMessage[]>([
    createMessage("assistant", "welcome"),
  ]);
  const [status, setStatus] = useState<StreamStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const applyEvent = useCallback((event: SSEEvent, assistantMessageId: string) => {
    if (event.type === "token") {
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantMessageId
            ? { ...message, content: `${message.content}${event.token}` }
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
