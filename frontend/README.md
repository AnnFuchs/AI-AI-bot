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
