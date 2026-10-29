<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import apiClient from '../../utils/api';
import TeamCard from './TeamCard.vue';

const props = defineProps<{
  hackathonId: string | number;
}>();

const teams = ref<any[]>([]);
const loading = ref(false);
const error = ref('');

// Преобразуем hackathonId в число
const hackathonIdNum = computed(() => {
  const id = typeof props.hackathonId === 'string' 
    ? parseInt(props.hackathonId, 10) 
    : props.hackathonId;
  if (isNaN(id)) {
    throw new Error('Invalid hackathon ID');
  }
  return id;
});

async function loadTeams() {
  loading.value = true;
  error.value = '';
  try {
    const response = await apiClient.get(`/api/teams/hackathons/${hackathonIdNum.value}`);
    teams.value = response.data;
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Ошибка';
  } finally {
    loading.value = false;
  }
}

onMounted(loadTeams);
</script>

<template>
  <div class="teams-list">
    <h2>Команды</h2>
    <div v-if="loading">Загрузка...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="teams.length === 0" class="empty">Нет команд</div>
    <div v-else class="cards-grid">
      <TeamCard v-for="team in teams" :key="team.id" :team="team" />
    </div>
  </div>
</template>

<style scoped lang="css">
.teams-list {
  margin-top: 2rem;
}
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
}
.error {
  color: var(--danger);
}
.empty {
  color: var(--muted);
  padding: 2rem;
  text-align: center;
}
</style>

