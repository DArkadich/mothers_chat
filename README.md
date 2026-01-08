# MothersChat

Короткая инструкция для локальной разработки, быстрого smoke-теста и автотестов.

---

## Local dev / Smoke / Tests ✅

- Поднять сервис (build + background):

```bash
docker compose up -d --build
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

---

## Переменные окружения (важные) 🔧

- `OPENAI_API_KEY` — ключ OpenAI (если используется настоящий OpenAI)
- `DATABASE_URL` — URL БД
- `FRONTEND_ORIGIN` — origin фронтенда для CORS
- `ENABLE_FAKE_OPENAI` — когда `1` используется встроенный фейк (для smoke)
- `DEFAULT_MODEL` — модель по умолчанию
- `TELEGRAM_BOT_TOKEN` — (рекомендуется) токен бота для верификации `initData` от Telegram WebApp

> API: `POST /api/chat/session` теперь может принимать `init_data` (предпочтительно) вместо `telegram_id`. Сервер проверит подпись `init_data` и извлечёт `user.id` (telegram_id). Если `init_data` отсутствует, `telegram_id` по-прежнему работает (удобно для локалки).

> Примечание по фронту: `assistant_slug` в API фильтруется по `Assistant.code` — договоритесь, что `assistant_slug == code` для фронта или используйте `assistant_code` во фронтенде, чтобы избежать путаницы.

---

## Почему это важно 💡

Любой разработчик (или ты-из-будущего) должен уметь поднять проект и проверить, что базовый сценарий работы жив — за ~5 минут.

---

## Схема и совместимость 🛠️

Проект умеет стартовать на старой схеме БД благодаря защитным проверкам, но рекомендуется прогонять миграции (alembic) и поддерживать схему в актуальном состоянии.

**Политика по проверкам схемы:** либо фиксируем схему и убираем runtime-проверки колонок (требует дисциплины миграций), либо официально поддерживаем несколько версий схемы — тогда проверки колонок становятся осознанной частью дизайна. Для MVP проверки оставлены для совместимости, но желательно регулярно прогонять миграции.

> 📌 См. `CONTRIBUTING.md` — **Migration policy** (правила по созданию миграций, пометки `# COMPAT: remove after migration <rev_id>` и чек-лист перед merge).

---

## CI (кратко)

Настроен GitHub Actions с двумя джобами: быстрые unit tests и smoke-compose (поднимает `docker compose` и прогоняет `./scripts/smoke_compose_check.sh --reset-volume`).
