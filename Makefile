.DEFAULT_GOAL := help
COMPOSE ?= docker compose

.PHONY: help env up start down stop restart build logs ps backend-logs bot-logs frontend-logs \
        migrate admin reset-admin-password db-shell backend-shell test clean nuke

help: ## Показать список команд
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

env: ## Создать .env из env.example со случайными секретами (если его нет)
	@if [ -f .env ]; then echo ".env уже существует"; else \
		cp env.example .env; \
		sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$$(openssl rand -hex 32)|; \
		        s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$$(openssl rand -hex 16)|; \
		        s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=$$(openssl rand -hex 8)|" .env; \
		echo ".env создан. Впишите TELEGRAM_BOT_TOKEN и TELEGRAM_BOT_USERNAME"; \
	fi

up: env ## Собрать и запустить всё в фоне
	$(COMPOSE) up --build -d
	@echo "Сайт: http://localhost  |  API: http://127.0.0.1:8000"

start: env ## Запустить в foreground (с логами)
	$(COMPOSE) up --build

down: ## Остановить и удалить контейнеры (данные БД сохраняются)
	$(COMPOSE) down

stop: ## Остановить контейнеры, не удаляя
	$(COMPOSE) stop

restart: ## Перезапустить сервисы
	$(COMPOSE) restart

build: ## Пересобрать образы
	$(COMPOSE) build

ps: ## Статус контейнеров
	$(COMPOSE) ps

logs: ## Логи всех сервисов
	$(COMPOSE) logs -f --tail=100

backend-logs: ## Логи backend
	$(COMPOSE) logs -f --tail=100 backend

bot-logs: ## Логи Telegram-бота
	$(COMPOSE) logs -f --tail=100 telegram-bot

frontend-logs: ## Логи frontend (nginx)
	$(COMPOSE) logs -f --tail=100 frontend

migrate: ## Применить миграции в запущенном backend
	$(COMPOSE) exec backend python -m app.cli migrate

admin: ## Создать админа из ADMIN_EMAIL / ADMIN_PASSWORD
	$(COMPOSE) exec backend python -m app.cli create-admin

reset-admin-password: ## Сбросить пароль админа на ADMIN_PASSWORD из .env
	$(COMPOSE) exec backend python -m app.cli create-admin --reset-password

db-shell: ## psql в контейнере БД
	$(COMPOSE) exec db sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

backend-shell: ## Shell в контейнере backend
	$(COMPOSE) exec backend sh

test: ## Тесты backend (нужен Docker для одноразового Postgres)
	cd backend && uv run pytest -q

clean: ## Удалить контейнеры и образы проекта (данные БД сохраняются)
	$(COMPOSE) down --rmi local

nuke: ## ВНИМАНИЕ: удалить контейнеры, образы и том с базой данных
	@printf "Это удалит все данные БД. Продолжить? [y/N] " && read ans && [ "$$ans" = "y" ]
	$(COMPOSE) down -v --rmi local
