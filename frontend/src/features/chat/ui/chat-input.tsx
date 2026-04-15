"use client";

import { useRef } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/shared/ui/button";

type ChatFormValues = {
  message: string;
};

type ChatInputProps = {
  disabled?: boolean;
  onSubmit: (message: string) => Promise<void> | void;
};

const TEXTAREA_MIN_HEIGHT = 48;

function resizeTextarea(textarea: HTMLTextAreaElement | null) {
  if (!textarea) {
    return;
  }

  textarea.style.height = `${TEXTAREA_MIN_HEIGHT}px`;
  textarea.style.height = `${Math.max(textarea.scrollHeight, TEXTAREA_MIN_HEIGHT)}px`;
}

export function ChatInput({ disabled = false, onSubmit }: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const form = useForm<ChatFormValues>({
    defaultValues: {
      message: "",
    },
  });
  const messageField = form.register("message");
  const messageValue = form.watch("message");
  const isMessageEmpty = messageValue.trim().length === 0;
  const isSubmitDisabled = disabled || isMessageEmpty;

  const submit = form.handleSubmit(async ({ message }) => {
    if (isSubmitDisabled) {
      return;
    }

    form.reset();
    resizeTextarea(textareaRef.current);
    await onSubmit(message);
  });

  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={(event) => {
        event.preventDefault();
      }}
    >
      <div className="flex flex-row items-end gap-2">
        <textarea
          aria-label="Сообщение Ай-Яй"
          className="h-12 max-h-40 w-full resize-none overflow-hidden rounded-xl border-2 border-black/20 bg-white px-4 py-2.5 text-lg leading-6 tracking-normal text-foreground placeholder:text-black/60 transition-[border-color,box-shadow] focus:border-primary/80 focus:shadow-[0_0_0_4px_hsl(var(--primary)/0.18)]
 focus:outline-none disabled:cursor-not-allowed disabled:border-black/20 disabled:bg-muted disabled:text-muted-foreground disabled:opacity-100 disabled:placeholder:text-muted-foreground"
          disabled={disabled}
          id="chat-message"
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault();
              void submit();
            }
          }}
          placeholder="Что бы вы хотели обсудить?"
          rows={1}
          {...messageField}
          onChange={(event) => {
            messageField.onChange(event);
            resizeTextarea(event.currentTarget);
          }}
          ref={(element) => {
            messageField.ref(element);
            textareaRef.current = element;
            resizeTextarea(element);
          }}
        />
        <Button
          aria-label="Отправить сообщение"
          className="size-12 shrink-0 border-2 border-transparent p-0 disabled:pointer-events-auto disabled:cursor-not-allowed disabled:border-black/20 disabled:bg-muted disabled:text-muted-foreground disabled:opacity-100 [&_svg]:size-6"
          disabled={isSubmitDisabled}
          onClick={() => {
            void submit();
          }}
          size="xl"
          type="button"
        >
          <SendIcon aria-hidden="true" />
        </Button>
      </div>
    </form>
  );
}

function SendIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg fill="none" viewBox="0 0 24 24" {...props}>
      <path d="M3 20V14L11 12L3 10V4L22 12L3 20Z" fill="currentColor" />
    </svg>
  );
}
