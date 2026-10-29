# Backend (API и Telegram-бот используют один образ)
# Контекст сборки: корень проекта (docker-compose)
FROM python:3.14-slim

# uv ставим из PyPI: так не нужен отдельный реестр ghcr.io
RUN pip install --no-cache-dir uv==0.13.1

WORKDIR /app

# venv вне /app, чтобы тома, смонтированные поверх /app, его не затирали
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Зависимости отдельным слоем: кэшируются, пока не изменились pyproject/uv.lock
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
# --locked: сборка падает, если uv.lock разошёлся с pyproject.toml
RUN uv sync --locked --no-dev

COPY backend/ /app/

# Запуск не от root
RUN useradd --system --no-create-home app && chown -R app /app
USER app

EXPOSE 8000

# Миграции и админ применяются до старта сервера (один раз, а не в каждом воркере)
CMD ["sh", "-c", "python -m app.cli migrate && python -m app.cli create-admin && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
