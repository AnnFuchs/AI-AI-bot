# AI-AI Bot

Чат-бот с искусственным интеллектом для консультации и поддержки пациентов, перенесших инсульт, и их родственников.

## Описание

AI-AI Bot — это интеллектуальная система поддержки, разработанная специально для помощи пациентам после инсульта и их близким. Бот предоставляет информацию и эмоциональную поддержку на основе современных технологий машинного обучения.

## Архитектура проекта

Проект построен на микросервисной архитектуре и состоит из следующих компонентов:

```
.
├── frontend/          # Next.js веб-приложение (React 19, TypeScript)
├── backend/           # FastAPI бэкенд с REST API
├── ai_layer/          # AI-сервис на базе LangGraph и GigaChat
├── nginx/             # Reverse proxy и балансировщик нагрузки
├── .github/           # CI/CD конфигурация
└── docker-compose.yml # Оркестрация сервисов
```

### Компоненты системы

- **Frontend**: Next.js 15 с React 19, TypeScript, Tailwind CSS, shadcn/ui
- **Backend**: FastAPI с PostgreSQL, SQLAlchemy, Alembic для миграций
- **AI Layer**: LangGraph + LangChain + GigaChat для обработки запросов
- **Векторная БД**: Qdrant для семантического поиска
- **Кеширование**: Redis для сессий и кеша
- **База данных**: PostgreSQL 16
- **Веб-сервер**: Nginx с поддержкой SSL

## Быстрый старт

### Требования

- Docker и Docker Compose
- Git

### Установка и запуск

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/AI-AI-bot.git
cd AI-AI-bot
```

2. Настройте переменные окружения:
```bash
# Backend
cp backend/infra/.env.example backend/infra/.env
# Отредактируйте backend/infra/.env

# AI Layer
cp ai_layer/.env.example ai_layer/.env
# Отредактируйте ai_layer/.env

# Frontend
cp frontend/.env.local.example frontend/.env.local
# Отредактируйте frontend/.env.local
```

3. Запустите все сервисы:
```bash
docker-compose up -d
```

4. Приложение будет доступно:
- Frontend: http://localhost
- Backend API: http://localhost/api
- API документация: http://localhost/api/docs

## Разработка

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Доступен на http://localhost:3000

**Полезные команды:**
- `npm run build` — сборка production версии
- `npm run lint` — проверка кода
- `npm run typecheck` — проверка типов TypeScript
- `npm run format` — форматирование кода

### Backend

```bash
cd backend/src
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Доступен на http://localhost:8000

**Миграции базы данных:**
```bash
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### AI Layer

```bash
cd ai_layer
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

Доступен на http://localhost:8001

**Тестирование:**
```bash
pytest tests/
```

## Docker

### Сборка образов

```bash
# Frontend
docker build -t aiai-frontend ./frontend

# Backend
docker build -t aiai-backend ./backend

# AI Layer
docker build -t aiai-ai-layer ./ai_layer
```

### Управление контейнерами

```bash
# Запуск всех сервисов
docker-compose up -d

# Остановка
docker-compose down

# Просмотр логов
docker-compose logs -f [service_name]

# Перезапуск сервиса
docker-compose restart [service_name]
```

## Технологический стек

### Frontend
- **Framework**: Next.js 15 (App Router)
- **UI**: React 19, TypeScript
- **Styling**: Tailwind CSS
- **Components**: shadcn/ui (Radix UI)
- **State**: Zustand
- **Forms**: React Hook Form + Zod
- **HTTP**: TanStack Query (React Query)
- **Markdown**: react-markdown

### Backend
- **Framework**: FastAPI
- **Database**: PostgreSQL 16 + SQLAlchemy 2.0
- **Migrations**: Alembic
- **Authentication**: JWT (python-jose) + bcrypt
- **Validation**: Pydantic v2
- **Async**: asyncpg
- **Scheduling**: APScheduler
- **Push notifications**: pywebpush

### AI Layer
- **Framework**: FastAPI
- **AI Orchestration**: LangGraph 1.1+
- **LLM Integration**: LangChain + GigaChat
- **Vector DB**: Qdrant Client
- **Retry Logic**: Tenacity
- **Testing**: pytest + pytest-asyncio

### Infrastructure
- **Web Server**: Nginx 1.25
- **Cache**: Redis 7.2
- **Containerization**: Docker + Docker Compose
- **SSL**: Let's Encrypt

## Конфигурация

### Переменные окружения

#### Backend (.env)
```env
POSTGRES_SERVER=db
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=aiai_db
SECRET_KEY=your_secret_key
AI_LAYER_URL=http://ai-layer:8001
```

#### AI Layer (.env)
```env
QDRANT_HOST=qdrant
QDRANT_PORT=6333
REDIS_URL=redis://redis:6379/0
BACKEND_BASE_URL=http://backend:8000
GIGACHAT_API_KEY=your_gigachat_key
APP_ENV=production
```

#### Frontend (.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost/api
```

## API Документация

После запуска проекта документация API доступна по адресам:
- Swagger UI: http://localhost/api/docs
- ReDoc: http://localhost/api/redoc
- OpenAPI Schema: http://localhost/api/openapi.json


## Вклад в проект

1. Создайте форк репозитория
2. Создайте ветку для фичи (`git checkout -b feature/amazing-feature`)
3. Закоммитьте изменения (`git commit -m 'Add amazing feature'`)
4. Отправьте в ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## Лицензия

Этот проект находится в стадии разработки (dev version).

## ⚠️ Disclaimer

Этот бот предоставляет информационную поддержку и не заменяет профессиональную медицинскую консультацию. При возникновении медицинских вопросов всегда обращайтесь к квалифицированному специалисту.

## Команда разработки

### Разработчики
- **[Осинский Сергей](https://github.com/osserg18)** — AI-слой и инфраструктура
- **[Фукс Анна](https://github.com/AnnFuchs)** — Backend и инфраструктура
- **[Назарова Полина](https://github.com/luvelayn)** — Frontend

### Менеджмент и дизайн
- **[Капутерка Эвелина](https://github.com/Ehvelina)** — Проджект-менеджер, UX-дизайнер

### Медицинские консультанты
- **Барбухатти Мария Кирилловна** — Врач-консультант
- **Комаревский Василий Александрович** — Врач-консультант

## Контакты

По вопросам и предложениям создавайте Issues в репозитории проекта.

---

**Статус**: 🚧 Development Version  