# Локальная установка и разработка

Запуск проекта без контейнеров для backend и frontend: удобно для разработки и отладки. В Docker остаётся только база данных. Запуск целиком в Docker: [QUICKSTART.md](./QUICKSTART.md) и [DOCKER_SETUP.md](./DOCKER_SETUP.md).

## Требования

- [uv](https://docs.astral.sh/uv/): менеджер Python-зависимостей. Нужную версию Python (3.14, см. `backend/.python-version`) uv скачает сам.
- Node.js 20+ и [pnpm](https://pnpm.io/installation) (версия указана в `frontend/package.json` в поле `packageManager`; `corepack enable` подтянет её автоматически).
- Docker: для PostgreSQL и для тестов.
- Git.

## 1. Окружение

```bash
git clone <repository-url>
cd hackathon-team-search

make env          # создаёт .env со случайными секретами
```

Откройте `.env` и впишите `TELEGRAM_BOT_TOKEN` и `TELEGRAM_BOT_USERNAME`. Затем добавьте адрес базы для локального запуска (пароль возьмите из `POSTGRES_PASSWORD` в том же файле):

```env
DATABASE_URL=postgresql://itam:<POSTGRES_PASSWORD>@localhost:5432/itam_hack
```

Backend читает `.env` из `backend/` и из корня проекта, поэтому отдельный файл в `backend/` не нужен. Docker Compose эту переменную игнорирует: внутри контейнеров адрес собирается из `POSTGRES_*`.

Для локального запуска полезно задать:

```env
FRONTEND_URL=http://localhost:3000    # адрес, который показывает бот
```

Swagger при запуске без Docker включён по умолчанию (http://localhost:8000/docs); в docker-compose он выключен, пока не задан `ENABLE_DOCS=true`.

## 2. База данных

```bash
docker compose up -d db
```

PostgreSQL слушает `127.0.0.1:5432`. Данные хранятся в томе `postgres-data` и переживают перезапуск.

## 3. Backend

```bash
cd backend

# Зависимости (создаёт .venv, версии берутся из uv.lock)
uv sync

# Миграции и админ (ADMIN_EMAIL и ADMIN_PASSWORD берутся из .env)
uv run python -m app.cli migrate
uv run python -m app.cli create-admin

# Сервер с автоперезагрузкой
uv run uvicorn app.main:app --reload --port 8000
```

Проверка: `curl http://localhost:8000/health` вернёт `{"status":"ok"}`.

Сменить пароль существующего админа: `uv run python -m app.cli create-admin --reset-password` (берёт `ADMIN_PASSWORD` из `.env`).

### Telegram-бот

В отдельном терминале:

```bash
cd backend
uv run python -m app.bot
```

Бот обращается к API по адресу `BACKEND_URL` (по умолчанию `http://localhost:8000`). Без запущенного бота войти через Telegram нельзя: коды выдаёт он.

### Управление зависимостями

```bash
uv add <пакет>              # добавить зависимость
uv add --dev <пакет>        # добавить в dev-группу
uv lock                     # обновить uv.lock после ручной правки pyproject.toml
uv sync --locked            # установить строго по lock-файлу
```

Коммитьте `pyproject.toml` и `uv.lock` вместе. Образ backend собирается с `--locked` и упадёт при расхождении.

## 4. Frontend

```bash
cd frontend

pnpm install
pnpm dev
```

Dev-сервер Vite запускается на http://localhost:3000 и проксирует `/api` на `http://localhost:8000`. Другой адрес API задаётся переменной `VITE_BACKEND_URL` (или `BACKEND_URL`) в `frontend/.env`.

Другие команды:

```bash
pnpm build                  # типы (vue-tsc) и production-сборка в dist/
pnpm preview                # просмотр собранной версии
pnpm add <пакет>            # добавить зависимость
```

Коммитьте `package.json` и `pnpm-lock.yaml` вместе. Скрипты установки в pnpm 12 по умолчанию заблокированы; для `esbuild` они разрешены в `frontend/pnpm-workspace.yaml`.

## 5. Тесты

```bash
make test
# или
cd backend && uv run pytest -q
```

Тесты идут на настоящем PostgreSQL. Если не задана переменная `TEST_DATABASE_URL`, поднимается одноразовый контейнер `postgres:16-alpine` (нужен Docker); схема создаётся теми же миграциями Alembic.

## Проверка работы

1. `GET http://localhost:8000/health` возвращает `{"status":"ok"}`.
2. Открывается Swagger: http://localhost:8000/docs.
3. На http://localhost:3000 нажмите вход через Telegram, напишите боту `/start` и введите код.
4. Вход админа: http://localhost:3000/admin/login, данные из `.env`.

## Решение проблем

**`uv run pytest` или `uvicorn` не находится.** Пересоздайте окружение: `uv sync --reinstall`.

**Backend не подключается к БД.** Проверьте, что контейнер `db` запущен (`docker compose ps`), и что пароль в `DATABASE_URL` совпадает с `POSTGRES_PASSWORD`. Если вы меняли пароль в `.env` после первого запуска БД, в томе остаётся старый: пересоздайте его (`make nuke`).

**Backend падает на старте с ошибкой про `SECRET_KEY`.** Ключ должен быть не короче 32 символов: `openssl rand -hex 32`.

**Порт 3000 или 8000 занят.** Порт Vite задаётся в `frontend/vite.config.ts`, порт backend флагом `--port` у `uvicorn`.

**Ошибки CORS в браузере.** При работе через `pnpm dev` запросы идут через прокси Vite и CORS не затрагивают. Если открываете фронтенд с другого адреса, добавьте его в `ALLOWED_ORIGINS`.

**Фронтенд не устанавливается или не собирается.** Удалите `frontend/node_modules` и выполните `pnpm install` заново.
