import Link from "next/link";

import type { ChatMessage } from "@/entities";
import { Button } from "@/shared/ui/button";

type MessageListProps = {
  messages: ChatMessage[];
  isStreaming: boolean;
};

export function MessageList({ messages, isStreaming }: MessageListProps) {
  return (
    <ol aria-label="Сообщения чата" className="flex flex-col gap-6">
      {messages.map((message, index) => {
        const isWelcomeMessage =
          index === 0 && message.role === "assistant" && message.content === "welcome";

        if (message.role === "user") {
          return (
            <li className="ml-auto flex max-w-[85%] flex-col" key={message.id}>
              <p className="mb-2 text-sm font-semibold text-muted-foreground">Вы:</p>
              <div className="rounded-xl bg-black/5 px-4 py-3 text-foreground">
                <p className="whitespace-pre-wrap text-lg leading-6">
                  {message.content}
                </p>
              </div>
            </li>
          );
        }

        return (
          <li
            className="w-full text-foreground sm:mr-auto sm:max-w-[88%]"
            key={message.id}
          >
            <p className="mb-2 text-sm font-semibold text-muted-foreground">
              Ай-Яй:
            </p>
            {isWelcomeMessage ? (
              <WelcomeMessage />
            ) : (
              <p className="whitespace-pre-wrap text-lg leading-6">
                {message.content || (isStreaming ? "Думаю..." : "")}
              </p>
            )}
          </li>
        );
      })}
    </ol>
  );
}

function WelcomeMessage() {
  return (
    <div className="space-y-4 text-lg leading-6">
      <p>
        Еще раз здравствуйте! Меня зовут Ай-Яй и я ваш помощник в жизни после
        инсульта.
      </p>
      <p>
        Буду рад помочь разобраться в происходящем и сориентироваться в море
        информации о заболевании и жизни с ним. Также помогу не пропустить
        важные симптомы и чувствовать себя спокойнее и увереннее!
      </p>
      <p>Еще есть много полезной информации в Базе знаний. Например:</p>
      <div className="flex flex-col items-start gap-2">
        <Button asChild className="w-fit" variant="chat">
          <Link href="/learn/articles/when-to-see-a-doctor">
            Когда стоит обратиться к врачу?
          </Link>
        </Button>
        <Button asChild className="w-fit" variant="chat">
          <Link href="/learn/articles/what-is-stroke">Что такое инсульт?</Link>
        </Button>
          <Button asChild className="w-fit" variant="chat">
              <Link href="/learn/articles/what-to-do-after-a-stroke">Инсульт – что делать дальше?</Link>
          </Button>
      </div>
      <p>Не стесняйтесь спрашивать, я постараюсь помочь! =)</p>
    </div>
  );
}
