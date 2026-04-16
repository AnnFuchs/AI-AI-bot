"use client";

import { useEffect, useRef } from "react";

import { useChatStream } from "../hooks/use-chat-stream";
import { ChatInput } from "./chat-input";
import { MessageList } from "./message-list";

export function ChatPage() {
  const { error, messages, sendMessage, status } = useChatStream();
  const messagesSectionRef = useRef<HTMLElement | null>(null);
  const isStreaming = status === "streaming";

  useEffect(() => {
    const frameId = requestAnimationFrame(() => {
      const messagesSection = messagesSectionRef.current;

      if (!messagesSection) {
        return;
      }

      messagesSection.scrollTo({
        top: messagesSection.scrollHeight,
        behavior: isStreaming ? "auto" : "smooth",
      });
    });

    return () => {
      cancelAnimationFrame(frameId);
    };
  }, [isStreaming, messages]);

  return (
    <main className="relative mx-auto flex h-[calc(100dvh-5rem)] w-full max-w-4xl flex-col overflow-hidden px-5">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-5 top-0 z-10 h-5 bg-gradient-to-b from-background to-transparent"
      />
      <section
        aria-live="polite"
        className="min-h-0 flex-1 overflow-y-auto pb-3 pt-5"
        ref={messagesSectionRef}
      >
        <MessageList isStreaming={isStreaming} messages={messages} />
      </section>

      <section className="relative z-10 bg-background pb-5 pt-3 before:pointer-events-none before:absolute before:inset-x-0 before:bottom-full before:h-5 before:bg-gradient-to-t before:from-background before:to-transparent">
        {error ? (
          <p className="mb-3 text-base text-destructive" role="alert">
            {error}
          </p>
        ) : null}
        <ChatInput disabled={isStreaming} onSubmit={sendMessage} />
      </section>
    </main>
  );
}
