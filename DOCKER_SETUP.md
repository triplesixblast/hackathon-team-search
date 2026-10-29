# Docker Setup

Запуск и сопровождение проекта через Docker Compose. Краткая версия: [QUICKSTART.md](./QUICKSTART.md), обзор проекта: [README.md](./README.md).

## Требования

- Docker 20.10+ и Docker Compose v2 (команда `docker compose`)
- `make` (необязательно, но все типовые операции собраны в `Makefile`)

```bash
docker --version
docker compose version
```

## Сервисы

| Сервис | Образ | Порт на хосте | Назначение |
|--------|-------|---------------|------------|
| `db` | `postgres:16-alpine` | `127.0.0.1:5432` | PostgreSQL, данные в томе `postgres-data` |
| `backend` | `backend/Dockerfile` | `127.0.0.1:8000` | API FastAPI |
| `telegram-bot` | тот же образ, что у backend | нет | бот, выдаёт коды входа |
| `frontend` | `frontend/Dockerfile` | `80` | Nginx со статикой и прокси `/api` |

Порты `db` и `backend` привязаны к `127.0.0.1`: снаружи доступен только сайт, а API идёт через `/api` в Nginx. Это сделано намеренно: API определяет IP клиента по `X-Forwarded-For`, и при прямом доступе заголовок можно подделать и обойти ограничение попыток входа.

Порядок старта: `db` (healthcheck `pg_isready`), затем `backend` (healthcheck `GET /health`), затем `telegram-bot`. Backend при запуске выполняет `python -m app.cli migrate` и `python -m app.cli create-admin`, затем запускает `uvicorn`.

## Настройка окружения

```bash
make env          # создаёт .env из env.example со случайными секретами, если файла ещё нет
```

После этого обязательно впишите в `.env`:

- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`: из @BotFather.

Compose не запустится, если не заданы `POSTGRES_PASSWORD`, `TELEGRAM_BOT_TOKEN`, `SECRET_KEY`, `ADMIN_EMAIL` или `ADMIN_PASSWORD`: в `docker-compose.yml` для них стоит проверка с понятным сообщением.

### Переменные

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `TELEGRAM_BOT_TOKEN` | нет | токен бота |
| `TELEGRAM_BOT_USERNAME` | пусто | имя бота без `@` |
| `SECRET_KEY` | нет | ключ подписи JWT, не короче 32 символов |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | срок жизни токена |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | нет | админ, создаётся при старте |
| `POSTGRES_USER`, `POSTGRES_DB` | `itam`, `itam_hack` | пользователь и база |
| `POSTGRES_PASSWORD` | нет | пароль БД |
| `CODE_EXPIRY_MINUTES` | `10` | срок жизни кода входа |
| `FRONTEND_URL` | `http://localhost` | адрес сайта (используется ботом) |
| `ALLOWED_ORIGINS` | localhost:80, :3000, :5173 | CORS, список через запятую |
| `TRUSTED_PROXY_HOPS` | `1` | число доверенных прокси перед API |
| `ENABLE_DOCS` | `false` | Swagger и ReDoc на `/docs` и `/redoc` |

Файл `.env` не попадает в git и в Docker-контекст.

## Запуск

```bash
make up           # собрать и запустить в фоне
make start        # то же, но с логами в терминале
```

Без `make`: `docker compose up --build -d`.

## Повседневные команды

```bash
make ps                    # статус контейнеров
make logs                  # логи всех сервисов
make backend-logs          # логи API
make bot-logs              # логи бота
make frontend-logs         # логи Nginx
make restart               # перезапуск
make stop                  # остановить, не удаляя контейнеры
make down                  # остановить и удалить контейнеры (БД сохраняется)
make build                 # пересобрать образы
make migrate               # применить миграции вручную
make admin                 # создать админа из ADMIN_EMAIL и ADMIN_PASSWORD
make reset-admin-password  # сбросить пароль админа на ADMIN_PASSWORD
make db-shell              # psql в контейнере БД
make backend-shell         # shell в контейнере backend
make clean                 # удалить контейнеры и образы проекта (БД сохраняется)
make nuke                  # удалить всё, включая данные БД (с подтверждением)
```

Эквиваленты без `make` смотрите в `Makefile`: это обычные вызовы `docker compose`.

## Сборка образов

**Backend** (`backend/Dockerfile`, контекст сборки: корень проекта). На базе `python:3.14-slim`, зависимости ставятся через uv по `backend/uv.lock` командой `uv sync --locked --no-dev`: сборка упадёт, если lock-файл разошёлся с `pyproject.toml`. Виртуальное окружение лежит в `/opt/venv`, процесс запускается не от root. Тот же образ использует `telegram-bot` с командой `python -m app.bot`.

**Frontend** (`frontend/Dockerfile`, контекст сборки: корень проекта). Двухэтапная сборка: на `node:22-alpine` ставится pnpm той же версии, что в `packageManager`, выполняется `pnpm install --frozen-lockfile` и `pnpm build`, затем статика копируется в `nginx:alpine`.

После изменения зависимостей обновляйте lock-файлы и коммитьте их: `uv lock` в `backend/` и `pnpm install` в `frontend/`.

## Nginx

`frontend/nginx.conf` отвечает за следующее:

- отдаёт собранную статику и для неизвестных путей возвращает `index.html` (маршруты Vue Router);
- проксирует `/api` на `backend:8000`, выставляя `X-Forwarded-For` в реальный адрес клиента (значение клиента перезаписывается, а не дополняется);
- кеширует хешированные ассеты из `/assets/` на год (`immutable`), а `index.html` отдаёт с `no-cache`, чтобы новая сборка подхватывалась сразу;
- добавляет заголовки безопасности: `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`. Они повторены в каждом `location`, потому что `add_header` внутри `location` отменяет заголовки уровня `server`;
- включает gzip.

HSTS в `nginx.conf` не задаётся: TLS терминируется на внешнем прокси, заголовок `Strict-Transport-Security` добавляйте там. CSP разрешает шрифты с Google Fonts и inline-стили (нужны Vue и SVG-фильтру навигации); при подключении других внешних ресурсов расширьте политику.

## Данные и резервные копии

База хранится в томе `postgres-data` и переживает `make down`. Удаляют её только `make nuke` и `docker compose down -v`.

```bash
# дамп
docker compose exec db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > backup.sql

# восстановление в пустую базу
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < backup.sql
```

## Продакшен

- Задайте сильные `SECRET_KEY`, `POSTGRES_PASSWORD`, `ADMIN_PASSWORD` (`make env` делает это автоматически).
- Оставьте `ENABLE_DOCS=false`.
- Укажите боевые адреса в `FRONTEND_URL` и `ALLOWED_ORIGINS`.
- TLS терминируйте на внешнем reverse proxy (Caddy, Traefik или Nginx на хосте) перед сервисом `frontend`. Тогда перед API окажутся два прокси: измените `TRUSTED_PROXY_HOPS` и то, как `frontend/nginx.conf` формирует `X-Forwarded-For`, иначе все клиенты будут выглядеть как адрес внешнего прокси и делить один лимит попыток.
- Не публикуйте порты `db` и `backend` наружу.
- Настройте регулярный `pg_dump`.

## Решение проблем

**Compose сообщает о незаданной переменной.** Выполните `make env` и заполните `TELEGRAM_BOT_TOKEN`.

**Порт занят.** Поменяйте левую часть в `ports`, например `"8080:80"` для сайта.

**Backend не становится healthy.** `make backend-logs`. Частые причины: слишком короткий `SECRET_KEY`, неверный `POSTGRES_PASSWORD` после смены в `.env` при уже созданном томе (пароль в томе остаётся прежним; смените его в БД или пересоздайте том через `make nuke`).

**Ошибки CORS.** Добавьте адрес сайта в `ALLOWED_ORIGINS` и перезапустите: `make restart`.

**Не приходят коды в Telegram.** `make bot-logs`; проверьте токен и что пользователь написал боту `/start`.

**Сайт открывается, но запросы к API падают.** Проверьте `make frontend-logs` и `curl http://127.0.0.1:8000/health`.

**Нужно полностью пересобрать.** `docker compose build --no-cache`, затем `make up`.
