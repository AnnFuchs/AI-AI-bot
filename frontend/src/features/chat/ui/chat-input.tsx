"use client";

import { useRef } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/shared/ui/button";
import { Textarea } from "@/shared/ui/textarea";

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
      <div className="flex min-w-0 flex-row items-end gap-2">
        <Textarea
          aria-label="Поле ввода сообщения"
          className="min-w-0 flex-1 resize-none overflow-hidden tracking-normal"
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
          className="size-12 shrink-0 [&_svg]:size-8"
          disabled={isSubmitDisabled}
          onClick={() => {
            void submit();
          }}
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
