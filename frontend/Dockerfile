# Stage 1: Build
FROM node:22-alpine AS builder

WORKDIR /app

# pnpm ставим той же версией, что указана в packageManager (package.json)
RUN npm install -g pnpm@12.15.0

# Контекст сборки - корень проекта, поэтому используем frontend/...
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./

# --frozen-lockfile: сборка падает, если pnpm-lock.yaml разошёлся с package.json
RUN pnpm install --frozen-lockfile

# Копирование исходного кода
# .dockerignore должен исключить node_modules, но на всякий случай копируем селективно
COPY frontend/src ./src
COPY frontend/public ./public
COPY frontend/index.html ./
COPY frontend/vite.config.ts ./
COPY frontend/tsconfig*.json ./

# Сборка приложения
RUN pnpm build

# Stage 2: Production
FROM nginx:alpine

# Копирование собранных файлов из builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Конфигурация nginx: /api проксируется на сервис backend
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Открываем порт
EXPOSE 80

# Запуск nginx
CMD ["nginx", "-g", "daemon off;"]



