<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { COOKIE_NAMES } from '../../config';
import apiClient from '../../utils/api';
import { setCookie } from '../../utils/auth';

const router = useRouter();

// Код, который пользователь получает от Telegram-бота
const code = ref('');
const loading = ref(false);
const error = ref('');

// Информация о боте (для ссылки)
const botLink = ref<string | null>(null);
const botUsername = ref<string | null>(null);

async function fetchBotLink() {
  try {
    const { data } = await apiClient.get('/api/auth/telegram/bot-link');
    botLink.value = data.bot_link;
    botUsername.value = data.bot_username;
  } catch {
    // молча игнорируем, просто не покажем ссылку
  }
}

onMounted(() => {
  fetchBotLink();
});

async function loginWithCode() {
  error.value = '';
  if (!code.value.trim()) {
    error.value = 'Введите код из Telegram-бота';
    return;
  }

  loading.value = true;
  try {
    const { data } = await apiClient.post('/api/auth/telegram/verify-code', {
      code: code.value.trim(),
    });

    // Сохраняем токен и id пользователя в cookie
    setCookie(COOKIE_NAMES.ACCESS_TOKEN, data.access_token);
    const userId = data.user?.user_id ?? data.user?.id;
    if (userId) {
      setCookie(COOKIE_NAMES.USER_ID, String(userId));
    }

    // Перенаправляем на дашборд
    router.push('/dashboard');
  } catch (e: any) {
    console.error('Login error:', e);
    // Обработка сетевых ошибок
    if (e?.networkError || !e?.response) {
      error.value = 'Ошибка сети. Проверьте подключение к интернету и попробуйте снова.';
    } else if (e?.response?.status === 401) {
      error.value = e?.response?.data?.detail || 'Неверный или истекший код. Получите новый код от бота.';
    } else if (e?.response?.status >= 500) {
      error.value = 'Ошибка сервера. Попробуйте позже.';
    } else {
      error.value =
        e?.response?.data?.detail ||
        e?.message ||
        'Произошла ошибка при проверке кода';
    }
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login-box">
    <button @click="router.push('/')" class="btn-back">← Назад</button>
    <h2>Вход через Telegram-бота</h2>

    <p class="description">
      1. Нажмите на кнопку ниже, чтобы открыть Telegram-бота и отправьте команду <b>/start</b>.<br />
      2. Получите от бота одноразовый код.<br />
      3. Вставьте код в поле ниже и нажмите «Войти».
    </p>

    <div v-if="botLink" class="bot-link-wrapper">
      <a :href="botLink" target="_blank" rel="noopener noreferrer" class="bot-link-button">
        Открыть Telegram-бота
      </a>
    </div>

    <form @submit.prevent="loginWithCode">
      <div>
        <label>Код из Telegram-бота:</label>
        <input v-model="code" type="text" placeholder="Например: 123456" required />
      </div>

      <button type="submit" :disabled="loading">
        {{ loading ? 'Проверяем код...' : 'Войти' }}
      </button>

      <p v-if="error" class="error"><b>{{ error }}</b></p>
    </form>
  </div>
</template>

<style scoped lang="css">
.login-box {
  max-width: 380px;
  width: 100%;
  margin: 0 auto;
  padding: 1.5rem 1.4rem 1.6rem;
  background: var(--glass);
  border: 1px solid var(--border);
  backdrop-filter: blur(var(--blur-strong)) saturate(1.5);
  -webkit-backdrop-filter: blur(var(--blur-strong)) saturate(1.5);
  border-radius: 24px;
  color: var(--text);
  box-shadow: var(--shadow-strong), inset 0 1px 0 rgb(var(--ink) / 0.35);
}

.description {
  font-size: 0.9rem;
  color: var(--muted);
  line-height: 1.6;
  margin-bottom: 1.4rem;
}

.bot-link-wrapper {
  margin-bottom: 1.2rem;
  text-align: center;
}

.bot-link-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 44px;
  padding: 0.8rem 1.2rem;
  border-radius: var(--radius-sm);
  background: #229ed9;
  color: #fff;
  font-weight: 700;
  text-decoration: none;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.bot-link-button:hover {
  transform: translate(-2px, -2px);
  box-shadow: 3px 3px 0 rgba(34, 158, 217, 0.45);
}

.login-box label {
  display: block;
  margin-top: 1.2rem;
  margin-bottom: 0.45rem;
  font-size: 0.9rem;
  font-weight: 600;
}
.login-box input {
  width: 100%;
  padding: 0.7rem 0.85rem;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: rgb(var(--ink) / 0.06);
  color: var(--text);
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
}
.login-box input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgb(var(--accent-rgb) / 0.25);
  background: rgb(var(--ink) / 0.1);
}

form button[type="submit"] {
  width: 100%;
  margin-top: 1.4rem;
}
button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
}

.error {
  margin-top: 0.8rem;
  color: var(--danger);
}

.btn-back {
  width: auto;
  min-height: 0;
  margin: 0 0 1.4rem -0.4rem;
  padding: 0.35rem 0.6rem;
  background: transparent;
  color: var(--muted);
  border: 0;
  box-shadow: none;
  font-size: 0.9rem;
  font-weight: 600;
}

.btn-back:hover {
  background: rgb(var(--ink) / 0.07);
  color: var(--text);
  transform: none;
  box-shadow: none;
}

.login-box h2 {
  margin-bottom: 1rem;
}

@media (min-width: 768px) {
  .login-box {
    padding: 2.2rem;
  }
}
</style>