# Ai-Ai Frontend

## Локальный запуск

```bash
npm install
npm run dev
```

Полезные проверки:

```bash
npm run typecheck
npm run lint
npm run build
```

## Архитектура

```text
src/
  app/                 маршруты Next.js, layout, providers, global CSS
  api/                 слой общения с backend и адаптеры
  entities/            общие доменные типы
  features/            продуктовые модули: чат, напоминания, самочувствие
  shared/              layout, UI-примитивы, PWA-утилиты и helpers
```

## Подключение к backend

Создайте `.env.local` рядом с `package.json`:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_USE_API_MOCKS=false
NEXT_PUBLIC_API_INCLUDE_CREDENTIALS=false
```

Если авторизация backend работает через HttpOnly cookies между разными origin,
поставьте `NEXT_PUBLIC_API_INCLUDE_CREDENTIALS=true`. В этом случае backend CORS
должен разрешать credentials и точный origin фронтенда, например
`http://localhost:3000`.

Чат отправляет запрос:

```text
POST /chat/stream
Content-Type: application/json
Accept: text/event-stream
```

Тело запроса:

```json
{
  "session_id": "browser-generated-uuid",
  "message": "Сообщение пользователя"
}
```

Фронтенд читает SSE-ответы такого вида:

```text
data: {"type":"token","token":"..."}

data: {"type":"done"}
```

## Авторизация

Вход отправляется в существующий endpoint:

```text
POST /auth/login
```

Регистрация отправляется в:

```text
POST /users/register
```

Форма входа отправляет поля `login` и `password`, где `login` — телефон
пользователя. Форма регистрации отправляет `phone` и `password`; после успешного
создания пользователя frontend автоматически вызывает `/auth/login`, сохраняет
`access_token` и `refresh_token` в `localStorage`, а последующие API-запросы
получают заголовок `Authorization: Bearer <access_token>`.
