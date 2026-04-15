"use client";

import { useChatStream } from "../hooks/use-chat-stream";
import { ChatInput } from "./chat-input";
import { MessageList } from "./message-list";

export function ChatPage() {
  const { error, messages, sendMessage, status } = useChatStream();
  const isStreaming = status === "streaming";

  return (
    <main className="mx-auto flex min-h-[calc(100dvh-4rem)] w-full max-w-4xl flex-col gap-5 px-5 pt-5">
      <section aria-live="polite" className="flex-1 pb-28">
        <MessageList isStreaming={isStreaming} messages={messages} />
      </section>

      <section className="sticky bottom-0 z-10 bg-background pb-5 pt-3">
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
