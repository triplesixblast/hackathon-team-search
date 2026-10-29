<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { COOKIE_NAMES } from '../../config';
import { setCookie } from '../../utils/auth';
import { adminApiClient } from '../../utils/api';

const router = useRouter();

const email = ref('');
const password = ref('');
const loading = ref(false);
const error = ref('');

async function loginAdmin() {
  error.value = '';
  loading.value = true;
  try {
    const { data } = await adminApiClient.post('/api/auth/admin/login', {
      email: email.value,
      password: password.value,
    });

    // Сохраняем токен админа в cookie
    setCookie(COOKIE_NAMES.ADMIN_TOKEN, data.access_token, 1);

    // Перенаправляем на админ-дашборд
    router.push('/admin');
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Ошибка входа (email/пароль)';
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login-box">
    <button @click="router.push('/')" class="btn-back">← Назад</button>
    <h2>Вход для администратора</h2>
    <form @submit.prevent="loginAdmin">
      <div>
        <label>Email:</label>
        <input v-model="email" type="email" required />
      </div>
      <div>
        <label>Пароль:</label>
        <input v-model="password" type="password" required />
      </div>
      <button type="submit" :disabled="loading">Войти</button>
      <p v-if="error" style="color: red;"><b>{{ error }}</b></p>
    </form>
  </div>
</template>

<style scoped lang="css">
.login-box {
  max-width: 350px;
  width: 100%;
  margin: 0 auto;
  padding: 1.5rem;
  background: var(--glass);
  border: 1px solid var(--border);
  backdrop-filter: blur(var(--blur-strong)) saturate(1.5);
  -webkit-backdrop-filter: blur(var(--blur-strong)) saturate(1.5);
  border-radius: 24px;
  color: var(--text);
}
.login-box label {
  display: block;
  margin-top: 1rem;
}
.login-box input {
  width: 100%;
  padding: 0.65rem 0.8rem;
  margin-top: 0.3rem;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: rgb(var(--ink) / 0.06);
  color: var(--text);
}

button {
  width: 100%;
  margin-top: 1.2rem;
}
button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
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
    padding: 2rem;
  }
}
</style>
