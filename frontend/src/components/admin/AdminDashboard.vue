<script setup lang="ts">
import { statusLabel } from '../../utils/statusLabels';
import { toast } from '../../composables/useFeedback';
import { ref, onMounted } from 'vue';
import { adminApiClient, API_BASE_URL } from '../../utils/api';

const hackathons = ref<any[]>([]);
const loading = ref(true);
const error = ref('');
const analytics = ref<any|null>(null);
const analyticsLoading = ref(false);
const analyticsError = ref('');

async function fetchHackathons() {
  loading.value = true;
  error.value = '';
  try {
    const response = await adminApiClient.get('/api/admin/hackathons');
    hackathons.value = response.data;
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Ошибка';
  } finally {
    loading.value = false;
  }
}

async function fetchAnalytics(hackathonId: number) {
  analytics.value = null;
  analyticsLoading.value = true;
  analyticsError.value = '';
  try {
    const response = await adminApiClient.get(`/api/admin/${hackathonId}/analytics`);
    analytics.value = response.data;
  } catch (e: any) {
    analyticsError.value = e?.response?.data?.detail || e?.message || 'Ошибка';
  } finally {
    analyticsLoading.value = false;
  }
}

async function downloadCSV(url: string, filename: string) {
  try {
    const response = await adminApiClient.get(url, {
      responseType: 'blob',
    });
    const href = URL.createObjectURL(response.data);
    const link = document.createElement('a');
    link.href = href;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(href);
  } catch (e: any) {
    toast.error('Ошибка скачивания CSV файла');
  }
}

onMounted(fetchHackathons);
</script>

<template>
  <div class="dashboard-wrapper">
    <h1>Админ-панель: хакатоны</h1>
    <div v-if="loading">Загрузка...</div>
    <div v-else-if="error"><b style="color:red;">{{ error }}</b></div>
    <div v-else>
      <div class="table-wrapper">
        <table class="hacks-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Название</th>
            <th>Старт</th>
            <th>Финиш</th>
            <th>Статус</th>
            <th>Аналитика</th>
            <th>Экспорт</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="h in hackathons" :key="h.id">
            <td>{{ h.id }}</td>
            <td>{{ h.name }}</td>
            <td>{{ h.start_date?.slice(0,10) }}</td>
            <td>{{ h.end_date?.slice(0,10) }}</td>
            <td>{{ statusLabel(h.status) }}</td>
            <td>
              <button @click="fetchAnalytics(h.id)">Аналитика</button>
            </td>
            <td><div class="btns">
              <button @click="downloadCSV(`${API_BASE_URL}/api/admin/${h.id}/participants/export`, `participants_${h.id}.csv`)">Участники CSV</button>
              <button @click="downloadCSV(`${API_BASE_URL}/api/admin/${h.id}/teams/export`, `teams_${h.id}.csv`)">Команды CSV</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      </div>
    </div>
    <div v-if="analyticsLoading" style="margin-top:;">Загрузка аналитики...</div>
    <div v-else-if="analyticsError" style="color: red;">Ошибка аналитики: {{ analyticsError }}</div>
    <div v-else-if="analytics" class="analytics-block">
      <h2>Аналитика по хакатону</h2>
      <ul>
        <li>Всего участников: <b>{{ analytics.total_participants }}</b></li>
        <li>Всего команд: <b>{{ analytics.total_teams }}</b></li>
        <li>Участников без команды: <b>{{ analytics.participants_without_team }}</b></li>
        <li>Участников в командах: <b>{{ analytics.participants_in_team }}</b></li>
        <li>Средний размер команды: <b>{{ analytics.average_team_size }}</b></li>
        <li>
          Навыки:<ul>
            <li v-for="(cnt, skill) in analytics.skills_frequency" :key="skill">{{ skill }}: {{ cnt }}</li>
          </ul>
        </li>
        <li>
          Опыт:<ul>
            <li v-for="(cnt, lvl) in analytics.experience_distribution" :key="lvl">{{ lvl }}: {{ cnt }}</li>
          </ul>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped lang="css">
.dashboard-wrapper {
  max-width: 1100px;
  width: 100%;
  margin: 1rem auto;
  padding: 1rem;
  background: var(--glass-strong);
  border-radius: 15px;
  color: var(--text);
}

.btns {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 6px;
  min-width: 140px;
  margin: 0 auto;
}

.dashboard-wrapper h1 {
  font-size: 1.5rem;
  margin-bottom: 1rem;
}

.table-wrapper {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  margin-top: 1.5rem;
}

.hacks-table {
  width: 100%;
  min-width: 800px;
  border-collapse: collapse;
}
.hacks-table th, .hacks-table td {
  border: 1px solid var(--hairline);
  padding: 0.5rem 0.7rem;
  font-size: 0.9rem;
}
.hacks-table th {
  background: var(--glass-strong);
  white-space: nowrap;
}
.hacks-table td:nth-last-child(-n+2) {
  text-align: center;
  vertical-align: middle;
}

button {
  padding: 0.4rem 0.8rem;
  background: var(--grad);
  color: var(--on-accent);
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-size: 0.85rem;
  white-space: nowrap;

}

.analytics-block {
  margin-top: 2.5rem;
  background: var(--glass-strong);
  padding: 1.2rem 2rem;
  border-radius: 10px;
}

@media (min-width: 768px) {
  .dashboard-wrapper {
    margin: 2rem auto;
    padding: 2rem;
  }
  .dashboard-wrapper h1 {
    font-size: 2rem;
    margin-bottom: 2rem;
  }

  .table-wrapper {
    margin-top: 2rem;
  }

  .hacks-table th, .hacks-table td {
    padding: 0.7rem 1rem;
    font-size: 1rem;
  }

  button {
    padding: 0.4rem 1.2rem;
    font-size: 1rem;
  }
}
</style>
