# Быстрый старт

Запуск ITAM Hack Platform за несколько минут. Подробности: [DOCKER_SETUP.md](./DOCKER_SETUP.md), для разработки без Docker: [INSTALLATION.md](./INSTALLATION.md).

## Что нужно

- Docker с Compose v2 (Windows и Mac: [Docker Desktop](https://www.docker.com/products/docker-desktop); Linux: `curl -fsSL https://get.docker.com | sh`)
- `make`
- Telegram-бот: создайте через [@BotFather](https://t.me/BotFather) и сохраните токен и имя пользователя бота

## Запуск

```bash
git clone <repository-url>
cd hackathon-team-search

# 1. Создать .env со случайными SECRET_KEY, POSTGRES_PASSWORD и ADMIN_PASSWORD
make env

# 2. Открыть .env и вписать TELEGRAM_BOT_TOKEN и TELEGRAM_BOT_USERNAME

# 3. Собрать и запустить
make up
```

Без `make` то же самое делается вручную: `cp env.example .env`, заполнить значения (`SECRET_KEY` генерируется командой `openssl rand -hex 32`), затем `docker compose up --build -d`.

Первая сборка занимает несколько минут. При старте backend сам применяет миграции и создаёт админа.

## Что открыть

| Что | Адрес |
|-----|-------|
| Сайт | http://localhost |
| Вход для админа | http://localhost/admin/login |
| API | http://127.0.0.1:8000 |
| Swagger | http://127.0.0.1:8000/docs (только при `ENABLE_DOCS=true` в `.env`) |

Логин и пароль админа лежат в `.env`: `ADMIN_EMAIL` и `ADMIN_PASSWORD`.

## Проверка

```bash
make ps                             # все сервисы в состоянии Up (healthy)
curl http://127.0.0.1:8000/health   # {"status":"ok"}
```

Вход участника: на сайте нажмите вход через Telegram, откройте бота, отправьте `/start`, введите полученный код на сайте.

## Первый хакатон

1. Войдите в админ-панель: http://localhost/admin/login.
2. Откройте раздел хакатонов и создайте новый.
3. Заполните форму и сохраните: хакатон появится у участников в списке.

## Частые команды

```bash
make logs          # логи всех сервисов
make down          # остановить (данные БД сохраняются)
make restart       # перезапустить
make help          # весь список
```

## Если что-то не работает

- **Compose пишет, что не задана переменная:** выполните `make env` и заполните `TELEGRAM_BOT_TOKEN`.
- **Порт занят:** поменяйте левую часть в `ports` в `docker-compose.yml`, например `"8080:80"`.
- **Ошибки CORS:** добавьте адрес сайта в `ALLOWED_ORIGINS` в `.env` и выполните `make restart`.
- **Бот молчит:** `make bot-logs`, проверьте токен.
- **Забыли пароль админа:** задайте новый `ADMIN_PASSWORD` в `.env` и выполните `make reset-admin-password`.

Остальное: раздел «Решение проблем» в [README.md](./README.md) и [DOCKER_SETUP.md](./DOCKER_SETUP.md).
