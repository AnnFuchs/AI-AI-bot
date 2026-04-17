import type { AuthToken, ChatRequest } from "@/entities";

type ApiRequestOptions<TBody> = {
  body?: TBody;
  signal?: AbortSignal;
};

const encoder = new TextEncoder();

function wait(ms: number, signal?: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    if (signal?.aborted) {
      reject(signal.reason);
      return;
    }

    const timeout = globalThis.setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        globalThis.clearTimeout(timeout);
        reject(signal.reason);
      },
      { once: true },
    );
  });
}

function sse(event: string, data: unknown) {
  return encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
}

const mockAuthToken: AuthToken = {
  access_token: "mock-access-token",
  refresh_token: "mock-refresh-token",
  token_type: "Bearer",
};

export const mockAdapter = {
  async request<TResponse, TBody>(
    path?: string,
    options?: ApiRequestOptions<TBody>,
  ) {
    void options;

    if (path === "/auth/login") {
      return mockAuthToken as TResponse;
    }

    if (path === "/users/register") {
      return undefined as TResponse;
    }

    if (path === "/users/me") {
      return (options?.body ?? {}) as TResponse;
    }

    return {} as TResponse;
  },

  stream<TBody>(path: string, options: ApiRequestOptions<TBody>) {
    if (path !== "/chat/stream") {
      throw new Error(`Для ${path} не настроен mock-stream`);
    }

    const request = options.body as ChatRequest | undefined;
    const prompt = request?.message?.trim();
    const tokens = [
      "Я рядом и внимательно вас слушаю. ",
      prompt
        ? "Пока backend не подключен, я отвечаю через mock-режим, но потоковая отправка уже работает. "
        : "Напишите, с чем вам нужна помощь сегодня. ",
      "Когда backend будет готов, этот же клиент будет получать ответы через POST-based SSE.",
    ];

    return new ReadableStream<Uint8Array>({
      async start(controller) {
        try {
          for (const token of tokens) {
            await wait(220, options.signal);
            controller.enqueue(sse("token", { token }));
          }

          await wait(220, options.signal);
          controller.enqueue(
            sse("text", {
              text: " Могу также показать памятку, если ответ кажется недостаточным.",
            }),
          );

          await wait(220, options.signal);
          controller.enqueue(
            sse("button", {
              label: "Открыть памятку",
              href: "/learn/articles/when-to-see-a-doctor",
            }),
          );

          await wait(220, options.signal);
          controller.enqueue(
            sse("alert", {
              payload: {
                red_flags: [
                  {
                    name: "headache",
                    level: "emergency",
                    description: "Внезапная сильная головная боль",
                    target_info: "Возможное субарахноидальное кровоизлияние",
                  },
                ],
                message: "Позвоните 112 немедленно!",
              },
            }),
          );

          await wait(220, options.signal);
          controller.enqueue(
            sse("sources", {
              payload: {
                confidence: 0.82,
                confidence_label: "high",
                sources: [
                  {
                    source: "Клинические_рекомендации_Ишемический_инсульт_2024.pdf",
                  },
                ],
                used_rag: true,
              },
            }),
          );

          controller.enqueue(sse("done", { conversationId: "mock-conversation" }));
          controller.close();
        } catch (error) {
          controller.error(error);
        }
      },
    });
  },
};
