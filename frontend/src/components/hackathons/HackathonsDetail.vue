<script setup lang="ts">
import { statusLabel } from '../../utils/statusLabels';
import { toast } from '../../composables/useFeedback';
import { ref, onMounted, computed } from 'vue';
import apiClient from '../../utils/api';
import CreateTeamForm from '../teams/CreateTeamForm.vue';
import TeamsList from '../teams/TeamsList.vue';

const props = defineProps<{
  id: string | number; // Параметр из роутера называется 'id'
}>();

const hackathon = ref<any>(null);
const loading = ref(false);
const error = ref('');
const registering = ref(false);
const teamCreated = ref(false);
const isRegistered = ref(false);

// Преобразуем id в число (из роутера приходит строка)
const hackathonIdNum = computed(() => {
  const id = typeof props.id === 'string' 
    ? parseInt(props.id, 10) 
    : props.id;
  if (isNaN(id)) {
    throw new Error('Invalid hackathon ID');
  }
  return id;
});

async function loadHackathon() {
  loading.value = true;
  error.value = '';
  try {
    const response = await apiClient.get(`/api/hackathons/${hackathonIdNum.value}`);
    hackathon.value = response.data;
    isRegistered.value = response.data.is_registered || false;
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Ошибка';
  } finally {
    loading.value = false;
  }
}

async function register() {
  if (isRegistered.value) {
    toast.info('Вы уже зарегистрированы на этот хакатон');
    return;
  }
  registering.value = true;
  try {
    await apiClient.post(`/api/hackathons/${hackathonIdNum.value}/register`, {});
    toast.success('Вы успешно зарегистрированы!');
    loadHackathon();
  } catch (e: any) {
    const errorMsg = e?.response?.data?.detail || e?.message || 'Ошибка регистрации';
    if (errorMsg.includes('уже зарегистрированы')) {
      toast.info('Вы уже зарегистрированы на этот хакатон');
      loadHackathon();
    } else {
      toast.error(errorMsg);
    }
  } finally {
    registering.value = false;
  }
}

function handleTeamCreated() {
  teamCreated.value = true;
  // Можно обновить список команд, если нужно
}

onMounted(loadHackathon);
</script>

<template>
  <div class="hackathon-detail">
    <div v-if="loading">Загрузка...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="hackathon" class="detail-card">
      <h1>{{ hackathon.name }}</h1>
      <div v-if="hackathon.description" class="description">{{ hackathon.description }}</div>
      <div class="info-grid">
        <div class="info-item">
          <strong>Начало:</strong> {{ new Date(hackathon.start_date).toLocaleString('ru-RU') }}
        </div>
        <div class="info-item">
          <strong>Окончание:</strong> {{ new Date(hackathon.end_date).toLocaleString('ru-RU') }}
        </div>
        <div class="info-item">
          <strong>Статус:</strong> <span class="status" :class="hackathon.status">{{ statusLabel(hackathon.status) }}</span>
        </div>
        <div class="info-item">
          <strong>Максимальный размер команды:</strong> {{ hackathon.max_team_size }}
        </div>
      </div>
      <div v-if="isRegistered && hackathon.status === 'upcoming'" class="registration-status">
        <span class="reg-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>
        </span>
        <p class="registered-message">Вы зарегистрированы на этот хакатон</p>
      </div>
      <button v-else-if="hackathon.status === 'upcoming'" @click="register" :disabled="registering" class="btn-register btn-primary">
        {{ registering ? 'Регистрация...' : 'Зарегистрироваться' }}
      </button>
      <div v-if="hackathon" class="teams-section">
        <!-- Форма создания команды показывается только для зарегистрированных пользователей на upcoming хакатонах -->
        <CreateTeamForm
          v-if="hackathon.status === 'upcoming' && isRegistered"
          :hackathon-id="hackathonIdNum"
          @team-created="handleTeamCreated"
        />
        <TeamsList :hackathon-id="hackathonIdNum" />
      </div>
    </div>
  </div>
</template>

<style scoped lang="css">
.hackathon-detail {
  max-width: 800px;
  width: 100%;
  margin: 0 auto;
}

.detail-card {
  background: var(--glass);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-soft);
  backdrop-filter: blur(var(--blur-soft)) saturate(1.4);
  -webkit-backdrop-filter: blur(var(--blur-soft)) saturate(1.4);
  border-radius: 12px;
  padding: 1.5rem;
  color: var(--text);
}
.detail-card h1 {
  color: var(--accent);
  margin-bottom: 1rem;
  font-size: 1.5rem;
}

.description {
  color: var(--muted);
  line-height: 1.6;
  margin-bottom: 2rem;
}

.info-grid {
  display: grid;
  gap: 1rem;
  margin-bottom: 2rem;
}

.info-item {
  color: var(--text);
}
/* Стили статусов теперь в глобальном style.css */

.btn-register {
  width: 100%;
}
.btn-register:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.registration-status {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  margin-bottom: 2rem;
  padding: 0.9rem 1.1rem;
  background: rgb(var(--accent-rgb) / 0.08);
  border: 1px solid rgb(var(--accent-rgb) / 0.35);
  border-radius: var(--radius-sm);
}

.reg-icon {
  flex: none;
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--accent);
  color: var(--on-accent);
}
.reg-icon svg {
  width: 16px;
  height: 16px;
}

.registered-message {
  color: var(--text);
  margin: 0;
  font-weight: 600;
  font-size: 1rem;
}

.error {
  color: var(--danger);
  text-align: center;
  padding: 2rem;
}

.teams-section {
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid var(--border);
}

.cannot-create-banner {
  background: var(--glass-strong);
  color: var(--text);
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  text-align: center;
}
.cannot-create-banner p { margin: 0; }

@media (min-width: 640px) {
  .detail-card {
    padding: 2rem;
  }
  .detail-card h1 {
    font-size: 2rem;
  }
}
</style>

