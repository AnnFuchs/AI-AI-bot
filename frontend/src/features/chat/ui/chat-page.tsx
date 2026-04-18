"use client";

import { useCallback, useLayoutEffect, useRef } from "react";

import { useChatStream } from "../hooks/use-chat-stream";
import { ChatInput } from "./chat-input";
import { MessageList } from "./message-list";

export function ChatPage() {
  const { error, messages, sendMessage, status } = useChatStream();
  const messagesSectionRef = useRef<HTMLElement | null>(null);
  const hasScrolledOnMountRef = useRef(false);
  const isStreaming = status === "streaming";

  const scrollToChatEnd = useCallback((behavior: ScrollBehavior = "smooth") => {
    const messagesSection = messagesSectionRef.current;

    if (!messagesSection) {
      return;
    }

    messagesSection.scrollTo({
      top: messagesSection.scrollHeight,
      behavior,
    });
  }, []);

  const handleSourcesOpen = useCallback(() => {
    requestAnimationFrame(() => {
      scrollToChatEnd();
    });
  }, [scrollToChatEnd]);

  useLayoutEffect(() => {
    if (!hasScrolledOnMountRef.current) {
      hasScrolledOnMountRef.current = true;
      scrollToChatEnd("auto");
      return;
    }

    const frameId = requestAnimationFrame(() => {
      scrollToChatEnd(isStreaming ? "auto" : "smooth");
    });

    return () => {
      cancelAnimationFrame(frameId);
    };
  }, [isStreaming, messages, scrollToChatEnd]);

  return (
    <main className="relative mx-auto flex h-[calc(100dvh-5rem)] w-full max-w-4xl flex-col overflow-hidden px-4 min-[375px]:px-5">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-4 top-0 z-10 h-3 bg-gradient-to-b from-background to-transparent min-[375px]:inset-x-5"
      />
      <section
        aria-live="polite"
        className="-mr-3 min-h-0 flex-1 overflow-y-auto pb-3 pr-3 pt-3"
        ref={messagesSectionRef}
      >
        <MessageList
          isStreaming={isStreaming}
          messages={messages}
          onSourcesOpen={handleSourcesOpen}
        />
      </section>

      <section className="relative z-10 bg-background pb-5 pt-3 before:pointer-events-none before:absolute before:inset-x-0 before:bottom-full before:h-3 before:bg-gradient-to-t before:from-background before:to-transparent">
        {error ? (
          <p className="mb-3 text-base leading-6 text-destructive" role="alert">
            {error}
          </p>
        ) : null}
        <ChatInput disabled={isStreaming} onSubmit={sendMessage} />
      </section>
    </main>
  );
}
