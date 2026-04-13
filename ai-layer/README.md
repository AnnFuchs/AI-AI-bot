# AI-Layer — Медицинский ИИ-ассистент Stroke Buddy

`ai-layer` — это основной интеллектуальный сервис приложения **Айяй**, предназначенного для поддержки пациентов, перенёсших инсульт. Это самостоятельный микросервис на базе FastAPI, который обрабатывает диалоги на естественном языке, мониторит симптомы, отвечает на вопросы по медицинской тематике, оказывает эмоциональную поддержку и управляет напоминаниями.

---

## Содержание

- [Обзор](#обзор)
- [Архитектура](#архитектура)
- [Структура проекта](#структура-проекта)
- [Граф диалога](#граф-диалога)
- [Модули](#модули)
- [API](#api)
- [Конфигурация](#конфигурация)
- [Запуск локально](#запуск-локально)
- [Docker](#docker)
- [Загрузка базы знаний](#загрузка-базы-знаний)
- [Тесты](#тесты)

---

## Обзор

Сервис принимает сообщение пользователя, классифицирует его намерение с помощью LLM и направляет его через конечный автомат на базе LangGraph к соответствующему обработчику. Ответы передаются клиенту потоково через **Server-Sent Events (SSE)**.

Основные возможности:

| Возможность | Описание |
|---|---|
| 🩺 **Проверка самочувствия** | Извлекает сущности симптомов из сообщения пользователя и оценивает медицинские тревожные признаки |
| 🚨 **Обнаружение тревожных признаков** | Детерминированный движок правил: FAST-симптомы, критическое давление, потеря сознания и др. |
| 📊 **Ввод медицинских данных** | Разбирает медицинские показатели (давление, пульс, сахар) и отправляет команду сохранения в бэкенд |
| 📚 **Обучение (RAG)** | Отвечает на вопросы об инсульте, препаратах и реабилитации с помощью векторной базы знаний Qdrant |
| 💬 **Эмоциональная поддержка** | Эмпатичные ответы без медицинских рекомендаций |
| ⏰ **Управление напоминаниями** | Извлекает параметры напоминания и отправляет команду upsert в бэкенд |
| 🔀 **Защита от нерелевантных тем** | Вежливо перенаправляет сообщения вне медицинской тематики |

---

## Архитектура

```
Клиент (Frontend / Backend)
        │  POST /chat/stream  (SSE)
        ▼
┌──────────────────────────────────────┐
│           FastAPI  (main.py)         │
│  – Валидация ChatRequest             │
│  – StreamingResponse (SSE)           │
└───────────────┬──────────────────────┘
                │
                ▼
┌──────────────────────────────────────┐
│     LangGraph Workflow (graph.py)    │
│                                      │
│  classifier_node                     │
│       │                              │
│       ├─ wellbeing_node              │
│       │       └─ red_flag_node       │
│       ├─ data_input_node             │
│       ├─ education_node  ◄── RAG     │
│       ├─ emotional_node              │
│       ├─ reminder_node               │
│       └─ off_topic_node              │
└──────────┬───────────────────────────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
LLMHandler    RAGService
(OpenAI)      (Qdrant)
```

- **LLMHandler** (`app/llm.py`) — обёртка над асинхронным клиентом OpenAI с логикой повторных попыток; поддерживает обычные и потоковые запросы, а также получение эмбеддингов.
- **RAGService** (`app/rag.py`) — выполняет поиск по векторным коллекциям Qdrant с косинусным сходством; поддерживает фильтрацию по подтипу инсульта.
- **LangGraph** — управляет многоходовым диалогом с хранением истории в памяти (per `session_id`).

---

## Структура проекта

```
ai-layer/
├── app/
│   ├── main.py        # FastAPI-приложение, lifespan, эндпоинт /chat/stream
│   ├── graph.py       # LangGraph: все узлы и логика маршрутизации
│   ├── schemas.py     # Pydantic-модели и TypedDict GraphState
│   ├── prompts.py     # Все системные промпты для LLM
│   ├── rag.py         # Векторный поиск Qdrant и загрузка документов
│   ├── rules.py       # Детерминированный движок тревожных признаков
│   ├── config.py      # Настройки из переменных окружения / .env
│   └── __init__.py
├── scripts/
│   └── ingest.py      # CLI-утилита для эмбеддинга и загрузки документов в Qdrant
├── tests/
│   ├── test_rules.py  # Юнит-тесты движка тревожных признаков
│   └── __init__.py
├── Dockerfile
└── requirements.txt
```

---

## Граф диалога

Каждое входящее сообщение проходит через следующие узлы LangGraph:

```
START
  └─► classifier_node        # Классификация намерения через LLM (JSON mode)
        │
        ├─► wellbeing_node    # Извлечение сущностей симптомов (JSON mode)
        │     └─► red_flag_node   # если симптомы обнаружены → движок правил
        │           └─► END
        │
        ├─► data_input_node   # Извлечение медицинских показателей → команда SAVE_DIARY_ENTRY
        │     └─► END
        │
        ├─► education_node    # RAG-поиск → потоковый ответ LLM
        │     └─► END
        │
        ├─► emotional_node    # Эмпатичный потоковый ответ
        │     └─► END
        │
        ├─► reminder_node     # Извлечение параметров → команда UPSERT_REMINDER
        │     └─► END
        │
        └─► off_topic_node    # Стандартный ответ с перенаправлением
              └─► END
```

### Уровни тревожных признаков

| Уровень | Пример триггера | Действие |
|---|---|---|
| `emergency` | FAST-симптомы (опущение лица, слабость руки, нарушение речи), потеря зрения, потеря сознания, интенсивность головной боли ≥ 8 | Инструкция вызвать 112, команда `ALERT_DOCTOR` в бэкенд |
| `urgent` | Артериальное давление ≥ 180 | Рекомендация обратиться к врачу в тот же день |
| `warning` | Общее самочувствие оценено как «плохое» | Отображение кнопки «Связаться с врачом» |

---

## Модули

### `schemas.py`
Содержит все модели данных:
- **`IntentEnum`** — 7 классов намерений для маршрутизации
- **`UserContext`** — профиль пациента (роль, тип/подтип инсульта, препараты)
- **`SymptomsData` / `SymptomEntity`** — результат структурированного извлечения симптомов
- **`RedFlag` / `RedFlagAlert`** — события тревожных признаков
- **`BackendCommand`** — типизированные команды для бэкенда (`SAVE_DIARY_ENTRY`, `UPSERT_REMINDER`, `ALERT_DOCTOR`)
- **`GraphState`** — полное состояние LangGraph (TypedDict)

### `prompts.py`
Все системные промпты для LLM:
- `CLASSIFIER_SYSTEM_PROMPT` — классификация намерения (вывод в JSON)
- `WELLBEING_SYSTEM_PROMPT` — извлечение сущностей симптомов (вывод в JSON)
- `DATA_INPUT_SYSTEM_PROMPT` — извлечение медицинских показателей (вывод в JSON)
- `EDUCATION_SYSTEM_PROMPT` — медицинские вопросы с опорой на RAG-контекст
- `EMOTIONAL_SYSTEM_PROMPT` — компаньон эмоциональной поддержки
- `REMINDER_SYSTEM_PROMPT` — извлечение параметров напоминания (вывод в JSON)

### `rules.py`
Чистый Python-движок правил, работающий **без LLM** для детерминированных решений по безопасности:
```python
RED_FLAG_RULES = [
    ("FAST_symptoms",         ..., "emergency"),
    ("vision_loss",           ..., "emergency"),
    ("loss_of_consciousness", ..., "emergency"),
    ("severe_headache",       ..., "emergency"),  # intensity >= 8
    ("high_bp_critical",      ..., "urgent"),     # value >= 180
    ("general_poor",          ..., "warning"),
]
```

### `rag.py`
Обёртка над `AsyncQdrantClient`:
- `search(collection, query, stroke_subtype, top_k)` — эмбеддинг запроса и поиск по косинусному сходству; поддерживает фильтрацию по полю метаданных `stroke_subtype`
- `ingest_documents(...)` — создаёт коллекцию при отсутствии и загружает объекты `PointStruct` (используется в `ingest.py`)

Используемые коллекции Qdrant: `stroke_types`, `medications`, `rehabilitation`, `risk_factors`

---

## API

### `POST /chat/stream`

Запускает потоковый диалог. Возвращает поток **Server-Sent Events**.

**Тело запроса:**
```json
{
  "user_id": "user-123",
  "session_id": "session-abc",
  "message": "У меня сильная головная боль и онемение руки",
  "user_context": {
    "user_id": "user-123",
    "role": "patient",
    "stroke_type": "ischemic",
    "stroke_subtype": "cardioembolic",
    "medications": ["Aspirin", "Warfarin"]
  }
}
```

**Типы SSE-событий:**

| Тип | Описание |
|---|---|
| `token` | Один токен потокового текста от LLM |
| `commands` | Массив команд для выполнения бэкендом |
| `alert` | Экстренный тревожный сигнал с полезной нагрузкой |
| `buttons` | Кнопки действий для отображения в UI |
| `error` | Сообщение об ошибке |
| `done` | Поток завершён |

**Пример SSE-событий:**
```
data: {"type": "token", "content": "Обратитесь"}
data: {"type": "token", "content": " к врачу"}
data: {"type": "alert", "payload": {"red_flags": [...], "message": "Позвоните 112 немедленно!"}}
data: {"type": "commands", "payload": [{"command_type": "ALERT_DOCTOR", "payload": {...}}]}
data: {"type": "done"}
```

### `GET /health`

Возвращает `{"status": "ok"}`. Используется для проверки работоспособности Docker / балансировщика нагрузки.

---

## Конфигурация

Настройки загружаются из переменных окружения или файла `.env` в директории `ai-layer`:

| Переменная | По умолчанию | Описание |
|---|---|---|
| `OPENAI_API_KEY` | *(обязательно)* | Ключ OpenAI API |
| `OPENAI_API_BASE` | `https://api.openai.com/v1` | Базовый URL API (поддерживает совместимые прокси) |
| `OPENAI_MODEL` | `gpt-4o-mini` | Модель для генерации текста |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Модель для эмбеддингов |
| `QDRANT_URL` | `http://localhost:6333` | URL экземпляра Qdrant |
| `QDRANT_COLLECTION_PREFIX` | `stroke_` | Префикс для имён коллекций Qdrant |
| `EMBEDDING_SIZE` | `1562` | Размерность вектора (должна совпадать с моделью эмбеддинга) |
| `APP_ENV` | `development` | Название окружения |
| `LOG_LEVEL` | `INFO` | Уровень логирования |

---

## Запуск локально

**Требования:** Python 3.11+, запущенный экземпляр Qdrant, ключ OpenAI API.

```bash
# 1. Установить зависимости
pip install -r ai-layer/requirements.txt

# 2. Создать .env файл
cp ai-layer/.env.example ai-layer/.env
# Заполнить OPENAI_API_KEY и QDRANT_URL

# 3. Запустить сервис
cd ai-layer
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

Сервис будет доступен по адресу `http://localhost:8001`.

---

## Docker

Сборка и запуск как отдельный контейнер:

```bash
docker build -t ai-layer ./ai-layer
docker run -p 8001:8001 --env-file ./ai-layer/.env ai-layer
```

Или через `docker-compose` из корня проекта (сервис определён как `ai-layer` в `docker-compose.yml`):

```bash
docker-compose up ai-layer
```

---

## Загрузка базы знаний

Скрипт `scripts/ingest.py` загружает документы форматов `.txt`, `.md` или `.pdf`, разбивает их на чанки (1000 символов, перекрытие 200), генерирует эмбеддинги через OpenAI и загружает их в коллекцию Qdrant.

```bash
cd ai-layer
python -m scripts.ingest --folder ./data/stroke_types --collection stroke_types
python -m scripts.ingest --folder ./data/medications   --collection medications
python -m scripts.ingest --folder ./data/rehab         --collection rehabilitation
python -m scripts.ingest --folder ./data/risk_factors  --collection risk_factors
```

---

## Тесты

```bash
cd ai-layer
pytest tests/
```

Текущее покрытие тестами (`tests/test_rules.py`):

| Тест | Что проверяет |
|---|---|
| `test_no_flags` | Отсутствие тревожных признаков при пустых данных симптомов |
| `test_fast_emergency` | Опущение лица вызывает экстренный FAST-сигнал (`emergency`) |
| `test_high_bp_urgent` | Давление ≥ 190 вызывает срочный сигнал повышенного давления (`urgent`) |