<script setup lang="ts">
import { ref, onMounted, defineProps } from 'vue';
import { adminApiClient } from '../../utils/api';

const props = defineProps<{ hackathonId: number }>();

const analytics = ref<any|null>(null);
const loading = ref(false);
const error = ref('');

async function fetchAnalytics() {
  loading.value = true;
  error.value = '';
  analytics.value = null;
  try {
    const response = await adminApiClient.get(`/api/admin/${props.hackathonId}/analytics`);
    analytics.value = response.data;
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Ошибка';
  } finally {
    loading.value = false;
  }
}

onMounted(fetchAnalytics);
</script>

<template>
  <div class="analytics-panel">
    <template v-if="loading">
      <div class="analytics-loading">Загрузка аналитики...</div>
    </template>
    <template v-else-if="error">
      <div class="analytics-error">Ошибка аналитики: {{ error }}</div>
    </template>
    <template v-else-if="analytics">
      <h3>Аналитика по хакатону №{{ props.hackathonId }}</h3>
      <ul>
        <li>Всего участников: <b>{{ analytics.total_participants }}</b></li>
        <li>Всего команд: <b>{{ analytics.total_teams }}</b></li>
        <li>В командах: <b>{{ analytics.participants_in_team }}</b></li>
        <li>Без команды: <b>{{ analytics.participants_without_team }}</b></li>
        <li>Средний размер команды: <b>{{ analytics.average_team_size }}</b></li>
        <li>
          Навыки:
          <ul class="dist-list">
            <li v-for="(cnt, skill) in analytics.skills_frequency" :key="skill">
              {{ skill }}: {{ cnt }}
            </li>
          </ul>
        </li>
        <li>
          Опыт:
          <ul class="dist-list">
            <li v-for="(cnt, lvl) in analytics.experience_distribution" :key="lvl">
              {{ lvl }}: {{ cnt }}
            </li>
          </ul>
        </li>
      </ul>
    </template>
  </div>
</template>

<style scoped lang="css">
.analytics-panel {
  background: var(--glass-strong);
  border-radius: 11px;
  padding: 2rem 2.1rem 1.5rem 2.1rem;
  margin: 2rem auto 0 auto;
  color: var(--text);
  max-width: 600px;
  box-shadow: var(--shadow-soft);
}
.analytics-panel h3 {
  color: var(--accent);
  margin-bottom: 1.3rem;
}
.analytics-panel ul {
  margin: 0.7em 0 0 0;
  padding-left: 1.3rem;
  font-size: 1.07rem;
  list-style-type: disc;
}
.analytics-panel li {
  margin-bottom: 0.63em;
}

.dist-list {
  list-style-type: circle;
  margin-top: 0.35em;
  margin-bottom: 0.7em;
}

.analytics-loading {
  color: var(--accent);
  padding: 1.4rem;
}

.analytics-error {
  color: var(--danger);
  padding: 1.4rem;
}
</style>
