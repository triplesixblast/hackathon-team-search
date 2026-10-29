<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { isUserAuthenticated, isAdminAuthenticated } from '../utils/auth';

const showAuthButtons = ref(true);

function checkAuth() {
  showAuthButtons.value = !isUserAuthenticated() && !isAdminAuthenticated();
}

let authTimer: ReturnType<typeof setInterval> | undefined;

onMounted(() => {
  checkAuth();
  // Проверяем каждую секунду на случай изменения cookies
  authTimer = setInterval(checkAuth, 1000);
});

onUnmounted(() => clearInterval(authTimer));
</script>

<template>
  <section class="home-hero">
    <p class="eyebrow">ITAM Hack / платформа команд</p>
    <h1>
      Собери команду.<br />
      <span class="hl">Выиграй хакатон.</span>
    </h1>
    <p class="lead">
      Находи единомышленников, создавай команды и отправляй заявки в пару касаний.
    </p>

    <div v-if="showAuthButtons" class="auth-section">
      <router-link to="/auth" class="auth-button">Войти через Telegram</router-link>
      <router-link to="/admin/login" class="btn-ghost">Вход для администратора</router-link>
    </div>

    <ul class="steps">
      <li><span>01</span>Войди через бота</li>
      <li><span>02</span>Выбери хакатон</li>
      <li><span>03</span>Собери команду</li>
    </ul>

  </section>
</template>

<style scoped lang="css">
.home-hero {
  padding: 2.5rem 0 1rem;
}
.eyebrow {
  font-family: var(--font-mono);
  font-size: 0.78rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 1.4rem;
}
.home-hero h1 {
  font-size: clamp(2rem, 8.5vw, 4.2rem);
  line-height: 1.02;
  font-weight: 700;
  margin-bottom: 1.4rem;
}
.hl {
  color: var(--accent);
}
.lead {
  max-width: 520px;
  color: var(--muted);
  font-size: 1.05rem;
  line-height: 1.55;
}
.auth-section {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  margin-top: 2rem;
  max-width: 340px;
}
.auth-button {
  padding: 1rem 1.4rem;
  font-size: 1.02rem;
}
.steps {
  list-style: none;
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.6rem;
  margin-top: 3rem;
}
.steps li {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  padding: 0.9rem 1rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--glass);
  font-weight: 600;
}
.steps span {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--accent);
}
@media (min-width: 720px) {
  .home-hero {
    padding-top: 4rem;
  }
  .auth-section {
    flex-direction: row;
    max-width: none;
  }
  .steps {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>
