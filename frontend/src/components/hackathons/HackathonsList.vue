<script setup lang="ts">
import { ref, onMounted } from 'vue';
import apiClient from '../../utils/api';
import HackathonsCard from './HackathonsCard.vue';

const hackathons = ref<any[]>([]);
const loading = ref(false);
const error = ref('');

async function loadHackathons() {
  loading.value = true;
  error.value = '';
  try {
    const response = await apiClient.get('/api/hackathons');
    hackathons.value = response.data;
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Ошибка';
  } finally {
    loading.value = false;
  }
}

onMounted(loadHackathons);
</script>

<template>
  <div class="hackathons-list">
    <div class="list-head">
      <div>
        <p class="eyebrow">Мероприятия</p>
        <h1>Хакатоны</h1>
      </div>
    </div>
    <div v-if="loading" class="loading">Загрузка...</div>
    <div v-else-if="error" class="error glass-panel">{{ error }}</div>
    <div v-else-if="hackathons.length === 0" class="empty glass-panel">Нет доступных хакатонов</div>
    <div v-else class="cards-grid card-grid">
      <HackathonsCard v-for="hackathon in hackathons" :key="hackathon.id" :hackathon="hackathon" />
    </div>
  </div>
</template>

<style scoped lang="css">
.hackathons-list {
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
}
.list-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  position: relative;
}
.eyebrow {
  color: var(--muted);
  font-size: 0.85rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}
.hackathons-list h1 {
  color: var(--text);
  margin: 0.35rem 0 0 0;
  font-size: 1.9rem;
}
.cards-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}
.error {
  color: var(--danger);
  text-align: center;
  padding: 1.5rem 1.2rem;
  font-size: 1rem;
  border: 1px solid rgb(var(--danger-rgb) / 0.35);
}

.empty {
  text-align: center;
  color: var(--muted);
  padding: 2rem 1rem;
}

.loading {
  padding: 1.5rem 1rem;
  color: var(--muted);
}

@media (min-width: 1024px) {
  .cards-grid {
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  }
}

@media (min-width: 640px) {
  .hackathons-list h1 {
    font-size: 2.2rem;
    margin-bottom: 1rem;
  }
  .cards-grid {
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1.5rem;
  }
  .error {
    padding: 2rem;
  }
  .empty {
    padding: 3rem;
  }
}
</style>

