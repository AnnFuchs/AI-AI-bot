"use client";

import { useEffect } from "react";

import { useChatStream } from "../hooks/use-chat-stream";
import { ChatInput } from "./chat-input";
import { MessageList } from "./message-list";

export function ChatPage() {
  const { error, messages, sendMessage, status } = useChatStream();
  const isStreaming = status === "streaming";

  useEffect(() => {
    const frameId = requestAnimationFrame(() => {
      window.scrollTo({
        top: document.documentElement.scrollHeight,
        behavior: isStreaming ? "auto" : "smooth",
      });
    });

    return () => {
      cancelAnimationFrame(frameId);
    };
  }, [isStreaming, messages]);

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-col gap-5 px-5 pt-5">
      <section aria-live="polite" className="flex-1">
        <MessageList isStreaming={isStreaming} messages={messages} />
      </section>

      <section className="sticky bottom-0 z-10 bg-background pb-5 pt-3 before:pointer-events-none before:absolute before:inset-x-0 before:bottom-full before:h-5 before:bg-gradient-to-t before:from-background before:to-transparent">
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
