import Link from "next/link";

import type { ChatMessage } from "@/entities";
import { Button } from "@/shared/ui/button";
import { ArrowRightIcon } from "@/shared/ui/icons/arrow-right-icon";

import { STROKE_INFO_ACTION } from "../lib/chat-actions";

function isExternalHref(href: string) {
  return href.startsWith("http://") || href.startsWith("https://");
}

function isStrokeInfoHref(href: string) {
  return href === STROKE_INFO_ACTION.href;
}

function formatConfidenceLabel(label?: string) {
  if (!label) {
    return undefined;
  }

  const labels: Record<string, string> = {
    high: "высокая",
    medium: "средняя",
    low: "низкая",
    insufficient: "недостаточная",
  };

  return labels[label] ?? label;
}

type MessageListProps = {
  messages: ChatMessage[];
  isStreaming: boolean;
  onSourcesOpen: () => void;
};

export function MessageList({
  messages,
  isStreaming,
  onSourcesOpen,
}: MessageListProps) {
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
                <p className="whitespace-pre-wrap break-words text-lg leading-6">
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
              <AssistantMessage
                isStreaming={isStreaming}
                message={message}
                onSourcesOpen={onSourcesOpen}
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}

function AssistantMessage({
  isStreaming,
  message,
  onSourcesOpen,
}: {
  isStreaming: boolean;
  message: ChatMessage;
  onSourcesOpen: () => void;
}) {
  return (
    <div className="space-y-3">
      <p className="whitespace-pre-wrap break-words text-lg leading-6">
        {message.content || (isStreaming ? "Думаю..." : "")}
      </p>
      {message.alerts?.length ? (
        <div className="space-y-2">
          {message.alerts.map((alert, index) => (
            <AlertBlock alert={alert} key={`${alert.message}-${index}`} />
          ))}
        </div>
      ) : null}
      {message.actions?.length ? (
        <div className="flex flex-col items-start gap-2">
          {message.actions.map((action) => (
            <Button
              asChild
              className="h-10 max-w-full justify-start overflow-hidden px-4 text-base min-[375px]:h-12 min-[375px]:text-lg"
              key={action.id}
              variant="chat"
            >
              <Link
                href={action.href}
                rel={isExternalHref(action.href) ? "noreferrer" : undefined}
                target={isExternalHref(action.href) ? "_blank" : undefined}
              >
                {action.label}
                {isStrokeInfoHref(action.href) ? (
                  <ArrowRightIcon aria-hidden="true" />
                ) : null}
              </Link>
            </Button>
          ))}
        </div>
      ) : null}
      {message.sources?.length ? (
        <div className="space-y-2">
          {message.sources.map((sources, index) => (
            <SourcesBlock
              key={index}
              onOpen={onSourcesOpen}
              sources={sources}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function AlertBlock({ alert }: { alert: NonNullable<ChatMessage["alerts"]>[number] }) {
  return (
    <section className="rounded-xl bg-destructive/10 px-4 py-3 text-lg leading-6 text-destructive">
      {alert.message ? <p className="font-semibold">{alert.message}</p> : null}
      {alert.red_flags.length ? (
        <ul className="mt-2 space-y-2">
          {alert.red_flags.map((flag, index) => (
            <li className="break-words" key={`${flag.name}-${index}`}>
              <p>{flag.description || flag.name}</p>
              {flag.target_info ? (
                <p className="text-base leading-6">{flag.target_info}</p>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function SourcesBlock({
  onOpen,
  sources,
}: {
  onOpen: () => void;
  sources: NonNullable<ChatMessage["sources"]>[number];
}) {
  const confidenceText =
    typeof sources.confidence === "number"
      ? `${Math.round(sources.confidence * 100)}%`
      : formatConfidenceLabel(sources.confidence_label);

  return (
    <div className="space-y-1 text-base leading-6 text-muted-foreground">
      {confidenceText ? <p>Уверенность в ответе: {confidenceText}</p> : null}
      {sources.sources.length ? (
        <details
          onToggle={(event) => {
            if (event.currentTarget.open) {
              onOpen();
            }
          }}
        >
          <summary className="cursor-pointer">Источники</summary>
          <ul className="mt-2 space-y-1">
            {sources.sources.map((source, index) => (
              <li className="break-words" key={`${source.source}-${index}`}>
                {source.url ? (
                  <Link
                    className="underline"
                    href={source.url}
                    rel="noreferrer"
                    target="_blank"
                  >
                    {source.title ?? source.source}
                  </Link>
                ) : (
                  (source.title ?? source.source)
                )}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
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
        <Button
          asChild
          className="h-10 max-w-full justify-start overflow-hidden px-4 text-base min-[375px]:h-12 min-[375px]:text-lg"
          variant="chat"
        >
          <Link href="/learn/articles/when-to-see-a-doctor">
            Когда стоит обратиться к врачу?
          </Link>
        </Button>
        <Button
          asChild
          className="h-10 max-w-full justify-start overflow-hidden px-4 text-base min-[375px]:h-12 min-[375px]:text-lg"
          variant="chat"
        >
          <Link href="/learn/articles/what-is-stroke">Что такое инсульт?</Link>
        </Button>
        <Button
          asChild
          className="h-10 max-w-full justify-start overflow-hidden px-4 text-base min-[375px]:h-12 min-[375px]:text-lg"
          variant="chat"
        >
          <Link href="/learn/articles/what-to-do-after-a-stroke">
            Инсульт – что делать дальше?
          </Link>
        </Button>
      </div>
      <p>Не стесняйтесь спрашивать, я постараюсь помочь! =)</p>
    </div>
  );
}
