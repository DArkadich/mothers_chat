# MothersChat

Telegram Mini App с AI-ассистентами для мам. Короткая инструкция для локальной разработки, быстрого smoke-теста и автотестов.

---

## Local dev / Smoke / Tests ✅

- Поднять сервис (build + background):

```bash
docker compose up -d --build
```

- Поднять сервис с реальным OpenAI (требует OPENAI_API_KEY):

```bash
OPENAI_API_KEY=your_key_here docker compose up -d --build
# или создать .env файл с OPENAI_API_KEY=your_key_here
```

- Полный прогон smoke (использует фейковый OpenAI):

```bash
ENABLE_FAKE_OPENAI=1 ./scripts/smoke_compose_check.sh --reset-volume
```

> ⚠️ **Опасно**: флаг `--reset-volume` удаляет данные (docker volume) — используйте с осторожностью.

- Прогон тестов в контейнере:

```bash
# если хотите запустить внутри контейнера
docker exec -it motherschat_backend pytest -q
# или с PYTHONPATH (если у вас такая практика)
docker exec -it motherschat_backend bash -lc 'PYTHONPATH=/app pytest -q'
```

- Проверка текущей ревизии Alembic:

```bash
docker compose exec backend sh -c 'cd backend && alembic current'
```

---

## Переменные окружения (важные) 🔧

- `OPENAI_API_KEY` — **обязательно** для использования реального OpenAI (без него будет ошибка, если `ENABLE_FAKE_OPENAI=0`)
- `DATABASE_URL` — URL БД (по умолчанию: `postgresql+psycopg2://motherschat:motherschat_password@db:5432/motherschat`)
- `FRONTEND_ORIGIN` — origin фронтенда для CORS (по умолчанию: `https://mamino.online`)
- `ENABLE_FAKE_OPENAI` — когда `1` используется встроенный фейк (для smoke/CI), по умолчанию `0` (реальный OpenAI)
- `DEFAULT_MODEL` — модель по умолчанию (по умолчанию: `gpt-4.1-mini`)
- `TELEGRAM_BOT_TOKEN` — (рекомендуется) токен бота для верификации `initData` от Telegram WebApp
- `FAKE_REPLY` — текст ответа для фейкового OpenAI (по умолчанию: `"Hello from fake model"`)

> **Важно:** По умолчанию `ENABLE_FAKE_OPENAI=0`, поэтому для работы приложения необходимо установить `OPENAI_API_KEY`. Для тестов и CI используйте `ENABLE_FAKE_OPENAI=1`.

> **API:** `POST /api/chat/session` принимает `init_data` (предпочтительно) или `telegram_id`. Сервер проверит подпись `init_data` и извлечёт `user.id` (telegram_id). Если `init_data` отсутствует, `telegram_id` по-прежнему работает (удобно для локалки).

> **Примечание:** `assistant_slug` в API фильтруется по `Assistant.code` или `Assistant.slug` (если доступно). Для фронтенда рекомендуется использовать `assistant_slug == code`.

---

## Почему это важно 💡

Любой разработчик (или ты-из-будущего) должен уметь поднять проект и проверить, что базовый сценарий работы жив — за ~5 минут.

---

## Схема БД и миграции 🛠️

Проект использует Alembic для управления миграциями. Текущие миграции:

1. `0001_initial_schema` — начальная схема (users, assistants, conversations, messages и др.)
2. `a1b2c3d4e5f6` — добавлена колонка `assistants.slug` (nullable)
3. `b2c3d4e5f6a7` — добавлена колонка `users.profile` (JSONB, nullable)

**Применение миграций:**

```bash
# В контейнере backend
docker compose exec backend sh -c 'cd backend && alembic upgrade head'

# Или локально (если настроен DATABASE_URL)
cd backend && alembic upgrade head
```

**Политика совместимости:** Проект умеет стартовать на старой схеме БД благодаря защитным проверкам, но рекомендуется прогонять миграции и поддерживать схему в актуальном состоянии.

> 📌 См. `CONTRIBUTING.md` — **Migration policy** (правила по созданию миграций, пометки `# COMPAT: remove after migration <rev_id>` и чек-лист перед merge).

---

## CI/CD (кратко)

Настроен GitHub Actions с двумя джобами:

1. **Unit tests** — быстрые тесты (pytest)
2. **Smoke-compose** — поднимает `docker compose`, прогоняет миграции и проверяет API через `./scripts/smoke_compose_check.sh --reset-volume`

Smoke-скрипт автоматически:
- Применяет миграции Alembic (`alembic upgrade head`)
- Выводит текущую ревизию (`alembic current`)
- Проверяет схему таблиц (`\d+ assistants`, `\d+ users`)
- Создаёт тестового ассистента
- Проверяет создание сессии и отправку сообщений через API

---

## Структура проекта

```
MothersChat/
├── backend/                    # Backend (FastAPI)
│   ├── app/                   # Основное приложение
│   │   ├── main.py            # FastAPI приложение
│   │   ├── db.py              # Настройка БД
│   │   └── models/            # Модели SQLAlchemy
│   │       ├── assistant.py
│   │       ├── chat.py
│   │       └── user.py
│   ├── core/                  # Ядро приложения
│   │   ├── limiter.py         # Rate limiting
│   │   └── telegram_auth.py  # Telegram WebApp аутентификация
│   ├── alembic/               # Миграции БД
│   │   ├── versions/          # Файлы миграций
│   │   └── env.py
│   ├── tests/                 # Тесты backend
│   │   └── test_chat.py
│   ├── models.py              # Модели (legacy, используется в миграциях)
│   ├── main_newold.py         # Основной файл API (текущий)
│   └── main.py                # Альтернативный файл API
│
├── frontend/app/              # Frontend (Telegram WebApp)
│   ├── index.html             # Главная страница
│   ├── main.js                # Основная логика
│   ├── styles.css             # Стили
│   └── [assets]               # Изображения и иконки
│
├── scripts/                   # Скрипты для CI/CD и деплоя
│   ├── smoke_compose_check.sh # Smoke-тесты
│   └── deploy_remote.sh       # Деплой на сервер
│
├── tests/                     # Общие тесты
│   ├── test_limits.py
│   └── test_telegram_auth.py
│
├── .github/workflows/         # GitHub Actions CI/CD
│   └── ci.yml
│
├── docker-compose.yml         # Docker Compose конфигурация
├── Dockerfile                 # Docker образ для backend
├── requirements.txt           # Python зависимости
├── conftest.py               # Pytest конфигурация
├── README.md                 # Этот файл
└── CONTRIBUTING.md           # Правила разработки
```
