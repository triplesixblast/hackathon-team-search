<script setup lang="ts">
import { statusLabel } from '../../utils/statusLabels';
import { ref, onMounted } from 'vue';
import { adminApiClient } from '../../utils/api';
import HackathonAdminEdit from './HackathonAdminEdit.vue';

const hackathons = ref<any[]>([]);
const loading = ref(false);
const error = ref('');
const showCreateForm = ref(false);
const editingId = ref<number | null>(null);

async function loadHackathons() {
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

function handleSaved() {
  showCreateForm.value = false;
  editingId.value = null;
  loadHackathons();
}

function handleCancelled() {
  showCreateForm.value = false;
  editingId.value = null;
}

onMounted(loadHackathons);
</script>

<template>
  <div class="hackathon-admin-list">
    <div class="header">
      <h1>Управление хакатонами</h1>
      <button @click="showCreateForm = true" class="btn-create">+ Создать хакатон</button>
    </div>
    <HackathonAdminEdit
      v-if="showCreateForm"
      mode="create"
      @saved="handleSaved"
      @cancelled="handleCancelled"
    />
    <HackathonAdminEdit
      v-if="editingId"
      mode="edit"
      :hackathon-id="editingId"
      @saved="handleSaved"
      @cancelled="handleCancelled"
    />
    <div v-if="loading">Загрузка...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else class="table-wrapper">
      <table class="hackathons-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Название</th>
            <th>Начало</th>
            <th>Окончание</th>
            <th>Статус</th>
            <th>Действия</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="h in hackathons" :key="h.id">
            <td>{{ h.id }}</td>
            <td>{{ h.name }}</td>
            <td>{{ new Date(h.start_date).toLocaleDateString('ru-RU') }}</td>
            <td>{{ new Date(h.end_date).toLocaleDateString('ru-RU') }}</td>
            <td><span class="status" :class="h.status">{{ statusLabel(h.status) }}</span></td>
            <td>
              <button @click="editingId = h.id" class="btn-edit">Редактировать</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped lang="css">
.hackathon-admin-list {
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
}

.header {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.header h1 {
  color: var(--accent);
  font-size: 1.5rem;
}

.btn-create {
  padding: 0.7rem 1.5rem;
  background: var(--accent);
  color: var(--on-accent);
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1rem;
}

.table-wrapper {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.hackathons-table {
  width: 100%;
  min-width: 800px;
  border-collapse: collapse;
  background: var(--glass);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-soft);
  backdrop-filter: blur(var(--blur-soft)) saturate(1.4);
  -webkit-backdrop-filter: blur(var(--blur-soft)) saturate(1.4);
  border-radius: 12px;
  overflow: hidden;
}
.hackathons-table th,
.hackathons-table td {
  padding: 0.7rem 0.5rem;
  text-align: left;
  border-bottom: 1px solid var(--border);
  font-size: 0.9rem;
}
.hackathons-table th {
  background: var(--glass-strong);
  color: var(--accent);
  white-space: nowrap;
}

/* Стили статусов теперь в глобальном style.css */

.btn-edit {
  padding: 0.5rem 1rem;
  background: var(--accent);
  color: var(--on-accent);
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.error {
  color: var(--danger);
  text-align: center;
  padding: 2rem;
}

@media (min-width: 768px) {
  .header {
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
  }
  .header h1 {
    font-size: 2rem;
  }

  .hackathons-table th,
  .hackathons-table td {
    padding: 1rem;
    font-size: 1rem;
  }
}
</style>

