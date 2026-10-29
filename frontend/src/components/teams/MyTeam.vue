<script setup lang="ts">
import { ref, onMounted } from 'vue';
import apiClient from '../../utils/api';

const teams = ref<any[]>([]);
const loading = ref(false);
const error = ref('');

async function loadMyTeams() {
  loading.value = true;
  error.value = '';
  try {
    const response = await apiClient.get('/api/teams/my');
    teams.value = response.data;
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Ошибка загрузки команд';
  } finally {
    loading.value = false;
  }
}

onMounted(loadMyTeams);
</script>

<template>
  <div class="my-team">
    <h1>Мои команды</h1>
    <div v-if="loading">Загрузка...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="teams.length === 0" class="empty">
      <p>Вы пока не состоите ни в одной команде.</p>
      <router-link to="/hackathons" class="btn-find btn-primary">Найти хакатон</router-link>
    </div>
    <div v-else class="teams-list">
      <div v-for="team in teams" :key="team.id" class="team-card">
        <h3>{{ team.name }}</h3>
        <p v-if="team.description">{{ team.description }}</p>
        <p class="hackathon-name">Хакатон: {{ team.hackathon_name }}</p>
        <router-link :to="`/teams/${team.id}`" class="btn-view btn-primary">Подробнее</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped lang="css">
.my-team {
  max-width: 800px;
  margin: 0 auto;
}
.my-team h1 {
  color: var(--accent);
  margin-bottom: 2rem;
}

.teams-list {
  display: flex;
  flex-direction: column;
  gap: 1.2rem;
}

.team-card {
  background: var(--glass);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-soft);
  backdrop-filter: blur(var(--blur-soft)) saturate(1.4);
  -webkit-backdrop-filter: blur(var(--blur-soft)) saturate(1.4);
  border-radius: 12px;
  padding: 1.5rem;
  color: var(--text);
}
.team-card h3 {
  margin: 0 0 0.5rem 0;
}

.hackathon-name {
  color: var(--muted);
  font-size: 0.9rem;
  margin-top: 0.3rem;
}

.empty {
  text-align: center;
  padding: 3rem;
  background: var(--glass);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-soft);
  backdrop-filter: blur(var(--blur-soft)) saturate(1.4);
  -webkit-backdrop-filter: blur(var(--blur-soft)) saturate(1.4);
  border-radius: 12px;
  color: var(--muted);
}

.btn-find,
.btn-view {
  display: inline-block;
  margin-top: 1rem;
}

.error {
  color: var(--danger);
  text-align: center;
  padding: 2rem;
}
</style>

