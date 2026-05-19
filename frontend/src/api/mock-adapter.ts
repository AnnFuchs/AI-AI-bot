import type { AuthToken, ChatRequest, ReminderOut, UserInfo } from "@/entities";

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

let mockUser: UserInfo = {
  phone: "+79990000000",
  daily_checkin_enabled: true,
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
};

let mockReminders: ReminderOut[] = [
  {
    id: "9a42761b-2047-4a8f-a02d-40b372284d3d",
    reminder_type: "medication",
    med_name: "Аспирин",
    time: "09:00:00",
    days: ["пн", "вт", "ср", "чт", "пт"],
    is_active: true,
    created_at: new Date().toISOString(),
  },
  {
    id: "56f2d578-42a2-48c4-b5c6-69c121c54c78",
    reminder_type: "daily_checkin",
    med_name: null,
    time: "20:00:00",
    days: [],
    is_active: true,
    created_at: new Date().toISOString(),
  },
];

export const mockAdapter = {
  async request<TResponse, TBody>(path?: string, options?: ApiRequestOptions<TBody>) {
    if (path === "/auth/login") {
      return mockAuthToken as TResponse;
    }

    if (path === "/users/register") {
      return undefined as TResponse;
    }

    if (path === "/users/me") {
      mockUser = {
        ...mockUser,
        ...((options?.body as Partial<UserInfo> | undefined) ?? {}),
      };

      return mockUser as TResponse;
    }

    if (path === "/users/me/timezone") {
      mockUser = {
        ...mockUser,
        ...((options?.body as Partial<UserInfo> | undefined) ?? {}),
      };

      return mockUser as TResponse;
    }

    if (path === "/reminders/vapid-public-key") {
      return {
        public_key:
          "BEl62iUYgUivxIkv69yViEuiBIa40HI80JtmQj6U6SI1rEVjT3Z7DcqFjo1zOj8bSh2j0sUB70Tz0Vfwo99YxUI",
      } as TResponse;
    }

    if (path === "/reminders/push-subscription") {
      return {} as TResponse;
    }

    if (path === "/reminders/") {
      return mockReminders as TResponse;
    }

    if (path?.startsWith("/reminders/")) {
      const reminderId = path.replace("/reminders/", "");
      mockReminders = mockReminders.filter((reminder) => reminder.id !== reminderId);

      return undefined as TResponse;
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
      "**Я рядом и внимательно вас слушаю.**\n\n",
      prompt ? `Вы спросили: _${prompt}_\n\n` : "Напишите, с чем вам нужна помощь сегодня.\n\n",
      "Пока backend не подключен, я отвечаю через mock-режим, но потоковая отправка уже работает.\n\n",
      "Вот пример markdown-разметки:\n\n",
      "- список отображается как список;\n",
      "- **важные слова** выделяются жирным;\n",
      "- ссылки открываются корректно: [База знаний](/learn).\n\n",
      "`POST /chat/stream` уже готов к SSE через fetch.",
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
              text: "\n\n> Могу также показать памятку, если ответ кажется недостаточным.",
            }),
          );

          await wait(220, options.signal);
          controller.enqueue(
            sse("button", {
              label: "Открыть памятку",
              href: "/learn",
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
                confidence_label: "high",
                sources: [
                  "Клинические рекомендации Ишемический инсульт 2024 https://cr.minzdrav.gov.ru/preview-cr/814_1",
                  "Учебный источник без ссылки 2026 None",
                ],
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
