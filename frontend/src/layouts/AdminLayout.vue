<script setup lang="ts">
import { adminLogout } from '../utils/auth';
</script>

<template>
  <div class="admin-layout">
    <header class="admin-header">
      <div class="admin-header-content">
        <h1>Админ-панель ITAM Hack</h1>
        <nav class="admin-nav">
          <router-link to="/admin">Дашборд</router-link>
          <router-link to="/admin/hackathons">Хакатоны</router-link>
          <button type="button" class="admin-logout" @click="adminLogout">Выйти</button>
        </nav>
      </div>
    </header>
    <main class="admin-main">
      <router-view />
    </main>
  </div>
</template>

<style scoped lang="css">
.admin-layout {
  min-height: 100vh;
  background: transparent;
  color: var(--text);
}

.admin-header {
  background: var(--glass);
  border-bottom: 1px solid var(--border);
  padding: 1rem 0;
  position: sticky;
  top: 0;
  z-index: 20;
  backdrop-filter: blur(var(--blur-strong)) saturate(1.5);
  -webkit-backdrop-filter: blur(var(--blur-strong)) saturate(1.5);
}
.admin-header h1 {
  font-size: 1.5rem;
  color: var(--accent);
  margin: 0;
}

.admin-header-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.admin-nav {
  display: flex;
  gap: 2rem;
}
.admin-nav a {
  color: var(--muted);
  text-decoration: none;
  font-size: 1.05rem;
  transition: color 0.15s;
}
.admin-nav a:hover,
.admin-nav a.router-link-active {
  color: var(--accent);
}

.admin-logout {
  min-height: 0;
  padding: 0.4rem 1rem;
  font-size: 0.95rem;
  background: var(--glass-strong);
  color: var(--text);
  border: 1px solid var(--hairline);
  box-shadow: none;
}

.admin-main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
}

@media (max-width: 1280px) {
  .admin-header-content {
    flex-direction: column;
    gap: 1rem;
  }
}
</style>