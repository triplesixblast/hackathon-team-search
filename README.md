# ITAM Hack Platform

Веб-платформа для поиска и формирования команд на хакатоны сообщества ITAM. Участники входят через Telegram, заполняют анкету, находят сокомандников и отправляют приглашения. Организаторы управляют хакатонами, смотрят аналитику и выгружают данные в CSV.

## Содержание

1. [Быстрый старт](#быстрый-старт)
2. [Документация](#документация)
3. [Стек и архитектура](#стек-и-архитектура)
4. [Структура проекта](#структура-проекта)
5. [Возможности](#возможности)
6. [API](#api)
7. [Настройка](#настройка)
8. [Тесты](#тесты)

## Быстрый старт

Нужны Docker с Compose v2 и `make`.

```bash
git clone <repository-url>
cd hackathon-team-search

# Создаёт .env из env.example и подставляет случайные SECRET_KEY, POSTGRES_PASSWORD и ADMIN_PASSWORD
make env

# Впишите в .env токен и имя бота из @BotFather:
#   TELEGRAM_BOT_TOKEN=...
#   TELEGRAM_BOT_USERNAME=...

# Сборка и запуск в фоне
make up
```

После запуска:

- сайт: http://localhost
- API: http://127.0.0.1:8000 (порт открыт только на localhost, снаружи API доступен через `/api` на сайте)
- Swagger: http://127.0.0.1:8000/docs, только если в `.env` задано `ENABLE_DOCS=true`
- вход админа: http://localhost/admin/login, логин и пароль из `ADMIN_EMAIL` и `ADMIN_PASSWORD` в `.env`

Остальные команды (`make logs`, `make migrate`, `make down` и т.д.) показывает `make help`.

## Документация

- [QUICKSTART.md](./QUICKSTART.md): запуск за пять минут
- [DOCKER_SETUP.md](./DOCKER_SETUP.md): Docker Compose, сервисы, переменные окружения, продакшен
- [INSTALLATION.md](./INSTALLATION.md): локальная разработка без Docker (uv и pnpm)

## Стек и архитектура

| Часть | Технологии |
|-------|------------|
| Backend | Python 3.14, FastAPI, SQLAlchemy 2 (async, asyncpg), Alembic, PyJWT |
| База данных | PostgreSQL 16 |
| Telegram-бот | python-telegram-bot, httpx |
| Frontend | Vue 3, TypeScript, Vite, Pinia, Vue Router |
| Инфраструктура | Docker Compose, Nginx |
| Менеджеры пакетов | uv (backend), pnpm (frontend) |

Сервисы в `docker-compose.yml`:

- `db`: PostgreSQL, данные в томе `postgres-data`
- `backend`: API; при старте применяет миграции и создаёт админа
- `telegram-bot`: выдаёт одноразовые коды входа, ходит в API с общим секретом `X-Bot-Secret`
- `frontend`: Nginx; раздаёт собранный фронтенд и проксирует `/api` на backend

Вход участника: пользователь пишет боту `/start`, получает код, вводит его на сайте (`POST /api/auth/telegram/verify-code`) и получает JWT. Код живёт `CODE_EXPIRY_MINUTES` минут, число неудачных попыток ограничено (10 за 10 минут).

## Структура проекта

```
hackathon-team-search/
├── docker-compose.yml
├── Makefile                    # команды: make help
├── env.example                 # шаблон .env
├── README.md, QUICKSTART.md, DOCKER_SETUP.md, INSTALLATION.md
│
├── backend/
│   ├── Dockerfile              # образ API и бота (uv)
│   ├── pyproject.toml          # зависимости
│   ├── uv.lock                 # зафиксированные версии
│   ├── alembic.ini
│   ├── migrations/             # миграции Alembic
│   ├── app/
│   │   ├── main.py             # приложение FastAPI, /health
│   │   ├── api/                # роутеры: auth, users, hackathons, teams, invitations, admin
│   │   ├── services/           # бизнес-логика
│   │   ├── models.py           # модели SQLAlchemy
│   │   ├── schemas.py          # схемы Pydantic
│   │   ├── config.py           # настройки из переменных окружения
│   │   ├── security.py         # JWT и хеширование паролей
│   │   ├── ratelimit.py        # ограничение неудачных попыток входа
│   │   ├── bot.py              # Telegram-бот
│   │   └── cli.py              # python -m app.cli migrate | create-admin
│   └── tests/                  # pytest
│
└── frontend/
    ├── Dockerfile              # multi-stage: сборка pnpm, затем Nginx
    ├── nginx.conf
    ├── package.json
    ├── pnpm-lock.yaml
    ├── vite.config.ts
    └── src/
        ├── components/         # страницы и компоненты
        ├── layouts/            # AppLayout (с мобильной навигацией), AdminLayout
        ├── router/             # Vue Router
        ├── store/              # Pinia
        └── style.css           # дизайн-токены и общие стили
```

## Возможности

Для участников:

- вход через Telegram без паролей, по одноразовому коду;
- просмотр хакатонов и регистрация на них;
- анкета: навыки, опыт, желаемая роль;
- поиск участников хакатона с фильтрами;
- создание команды (создатель становится капитаном), передача роли капитана, выход из команды;
- приглашения в команду и заявки на вступление: отправка, принятие, отклонение;
- счётчик непросмотренных уведомлений в навигации;
- один участник не может состоять в двух командах одного хакатона.

Для организаторов:

- создание и редактирование хакатонов;
- аналитика по хакатону;
- экспорт участников и команд в CSV;
- ручное добавление участника в команду.

## API

Все эндпоинты начинаются с `/api`. Полная схема доступна в Swagger (`/docs`) при `ENABLE_DOCS=true`. Проверка работоспособности: `GET /health`.

| Группа | Эндпоинты |
|--------|-----------|
| Авторизация | `POST /api/auth/telegram/generate-code` (вызывает бот), `POST /api/auth/telegram/verify-code`, `GET /api/auth/telegram/bot-link`, `POST /api/auth/admin/login` |
| Пользователи | `GET`, `PUT /api/users/me`; `GET /api/users/{id}`; `GET /api/users/hackathons/{id}/participants` |
| Хакатоны | `GET /api/hackathons`; `GET /api/hackathons/{id}`; `POST /api/hackathons/{id}/register`; `POST /api/hackathons` и `PUT /api/hackathons/{id}` (админ) |
| Команды | `POST /api/teams`; `GET /api/teams/my`; `GET /api/teams/hackathons/{id}`; `GET`, `PATCH`, `DELETE /api/teams/{id}`; `POST /api/teams/{id}/apply`, `/invite`, `/leave`, `/transfer-captain`; `DELETE /api/teams/{id}/members/{user_id}` |
| Приглашения | `GET /api/invitations`; `GET /api/invitations/applications`; `POST /api/invitations/{id}/accept`, `/approve`, `/reject`; `DELETE /api/invitations/{id}` |
| Админка | `GET /api/admin/hackathons`; `GET /api/admin/{id}/analytics`; `GET /api/admin/{id}/participants/export`, `/teams/export`; `POST /api/admin/hackathons/{id}/assign-user` |

## Настройка

Все переменные описаны в `env.example`. Основные:

| Переменная | Назначение |
|------------|------------|
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME` | бот из @BotFather (токен обязателен для запуска) |
| `SECRET_KEY` | ключ подписи JWT, не короче 32 символов (`openssl rand -hex 32`) |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | учётная запись админа, создаётся при старте backend |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | база данных; `DATABASE_URL` compose собирает сам |
| `ALLOWED_ORIGINS` | список адресов для CORS через запятую |
| `TRUSTED_PROXY_HOPS` | сколько доверенных прокси перед API (в compose это 1, Nginx) |
| `ENABLE_DOCS` | включить Swagger и ReDoc (по умолчанию в compose выключено) |

Сменить пароль админа: поменяйте `ADMIN_PASSWORD` в `.env` и выполните `make reset-admin-password`. Пароль существующего админа без этой команды не перезаписывается.

## Тесты

```bash
make test
```

Тесты backend идут на настоящем PostgreSQL: без `TEST_DATABASE_URL` поднимается одноразовый контейнер, поэтому нужен Docker. Схема создаётся теми же миграциями Alembic, что и в продакшене.