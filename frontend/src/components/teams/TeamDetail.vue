<script setup lang="ts">
import { statusLabel } from '../../utils/statusLabels';
import { toast, confirmDialog } from '../../composables/useFeedback';
import { ref, onMounted, computed } from 'vue';
import apiClient from '../../utils/api';
import InvitePanel from './InvitePanel.vue';

const props = defineProps<{
  id: string | number; // Параметр из роутера называется 'id'
}>();

const team = ref<any>(null);
const currentUser = ref<any>(null);
const loading = ref(false);
const error = ref('');
const applying = ref(false);
const applyError = ref('');
const applySuccess = ref('');
const isMember = ref(false);
const removingMember = ref(false);
const leavingTeam = ref(false);

// Преобразуем id в число (из роутера приходит строка)
const teamIdNum = computed(() => {
  const id = typeof props.id === 'string' 
    ? parseInt(props.id, 10) 
    : props.id;
  if (isNaN(id)) {
    throw new Error('Invalid team ID');
  }
  return id;
});

// Проверяем, является ли текущий пользователь капитаном
const isCaptain = computed(() => {
  return currentUser.value && team.value && currentUser.value.id === team.value.captain_id;
});

// Проверяем, полная ли команда
const isTeamFull = computed(() => {
  if (!team.value) return false;
  if (!team.value.max_team_size) return false;
  const currentCount = team.value.members?.length || 0;
  return currentCount >= team.value.max_team_size;
});

async function loadCurrentUser() {
  try {
    const response = await apiClient.get('/api/users/me');
    currentUser.value = response.data;
  } catch (e: any) {
    console.error('Failed to load current user:', e);
  }
}

async function loadTeam() {
  loading.value = true;
  error.value = '';
  try {
    const response = await apiClient.get(`/api/teams/${teamIdNum.value}`);
    team.value = response.data;
    // Проверяем, является ли пользователь участником команды
    isMember.value = team.value.members?.some((m: any) => m.id === currentUser.value?.id) || false;
    // Убеждаемся, что max_team_size загружен
    if (!team.value.max_team_size && team.value.hackathon) {
      team.value.max_team_size = team.value.hackathon.max_team_size;
    }
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Ошибка';
  } finally {
    loading.value = false;
  }
}

async function applyToTeam() {
  if (!team.value || !currentUser.value) return;
  
  applying.value = true;
  applyError.value = '';
  applySuccess.value = '';
  
  try {
    // Отправляем запрос капитану (создаем приглашение от пользователя к капитану)
    // Но в текущей системе приглашения отправляет только капитан
    // Поэтому создадим эндпоинт для запроса на вступление
    await apiClient.post(`/api/teams/${teamIdNum.value}/apply`);
    applySuccess.value = 'Заявка отправлена капитану команды!';
    setTimeout(() => {
      applySuccess.value = '';
    }, 3000);
  } catch (e: any) {
    applyError.value = e?.response?.data?.detail || e?.message || 'Ошибка отправки заявки';
    setTimeout(() => {
      applyError.value = '';
    }, 3000);
  } finally {
    applying.value = false;
  }
}

function handleInviteSent() {
  // Обновляем информацию о команде после отправки приглашения
  loadTeam();
}

async function removeMember(userId: number) {
  if (!(await confirmDialog('Вы уверены, что хотите исключить этого участника из команды?', { confirmText: 'Исключить', danger: true }))) return;
  
  removingMember.value = true;
  try {
    await apiClient.delete(`/api/teams/${teamIdNum.value}/members/${userId}`);
    toast.success('Участник исключен из команды');
    loadTeam();
  } catch (e: any) {
    toast.error(e?.response?.data?.detail || e?.message || 'Ошибка при исключении участника');
  } finally {
    removingMember.value = false;
  }
}

async function leaveTeam() {
  if (!(await confirmDialog('Вы уверены, что хотите покинуть команду?', { confirmText: 'Покинуть', danger: true }))) return;
  
  leavingTeam.value = true;
  try {
    await apiClient.post(`/api/teams/${teamIdNum.value}/leave`);
    // Перенаправляем на страницу команд
    window.location.href = '/team';
  } catch (e: any) {
    toast.error(e?.response?.data?.detail || e?.message || 'Ошибка при выходе из команды');
  } finally {
    leavingTeam.value = false;
  }
}

onMounted(async () => {
  await loadCurrentUser();
  await loadTeam();
});
</script>

<template>
  <div class="team-detail">
    <div v-if="loading">Загрузка...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="team" class="detail-card glass-panel floating">
      <h1>{{ team.name }}</h1>
      <p v-if="team.description" class="description">{{ team.description }}</p>
      <div class="info">
        <div v-if="team.hackathon"><strong>Хакатон:</strong> {{ team.hackathon.name }}</div>
        <div><strong>Капитан:</strong> {{ team.captain?.full_name }}</div>
        <div><strong>Статус:</strong> <span class="status" :class="team.status">{{ statusLabel(team.status) }}</span></div>
        <div><strong>Участников:</strong> {{ team.members?.length || 0 }}<span v-if="team.max_team_size"> / {{ team.max_team_size }}</span></div>
      </div>
      <div v-if="team.members && team.members.length > 0" class="members">
        <h3>Участники:</h3>
        <div class="members-list">
          <div v-for="member in team.members" :key="member.id" class="member-item glass-panel">
            <div class="member-header">
              <strong>{{ member.full_name }}</strong>
              <div v-if="isCaptain && member.id !== team.captain_id" class="member-actions">
                <button @click="removeMember(member.id)" class="btn-remove btn-ghost">Исключить</button>
              </div>
              <div v-else-if="isMember && !isCaptain && member.id === currentUser?.id" class="member-actions">
                <button @click="leaveTeam" class="btn-leave btn-ghost">Выйти</button>
              </div>
            </div>
            <span v-if="member.role_preference" class="role">{{ member.role_preference }}</span>
            <div v-if="member.skills && member.skills.length > 0" class="skills">
              <span v-for="skill in member.skills" :key="skill" class="skill-tag">{{ skill }}</span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Кнопка подачи заявки - для не капитана и не участника -->
      <div v-if="!isCaptain && !isMember && team && team.status === 'open' && !isTeamFull" class="apply-section">
        <button @click="applyToTeam" :disabled="applying" class="btn-apply btn-primary">
          {{ applying ? 'Отправка...' : 'Подать заявку в команду' }}
        </button>
        <p v-if="applyError" class="apply-error">{{ applyError }}</p>
        <p v-if="applySuccess" class="apply-success">{{ applySuccess }}</p>
      </div>
      
      <!-- Сообщение если команда полная -->
      <div v-if="!isCaptain && !isMember && team && team.status === 'open' && isTeamFull" class="team-full-message glass-panel">
        <p>Команда заполнена ({{ team.members?.length || 0 }} / {{ team.max_team_size }})</p>
      </div>
      
      <!-- Сообщение для участника -->
      <div v-if="isMember && !isCaptain" class="member-status glass-panel">
        <p class="member-message">Вы являетесь участником этой команды</p>
      </div>
      
      <!-- Панель приглашения - только для капитана -->
      <InvitePanel 
        v-if="isCaptain && team"
        :team-id="teamIdNum"
        :hackathon-id="team.hackathon_id"
        @invite-sent="handleInviteSent"
      />
    </div>
  </div>
</template>

<style scoped lang="css">
.team-detail {
  max-width: 800px;
  width: 100%;
  margin: 0 auto;
  position: relative;
  overflow: visible;
}

.detail-card {
  padding: 1.6rem;
  color: var(--text);
  position: relative;
}
.detail-card h1 {
  color: var(--text);
  margin-bottom: 1rem;
  font-size: 1.6rem;
}

.description {
  color: var(--muted);
  margin-bottom: 1.5rem;
}

.info {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 2rem;
}

.status.open {
  background: rgb(var(--ok-rgb) / 0.15);
  color: var(--accent-3);
  border-color: rgb(var(--ok-rgb) / 0.35);
}
.status.closed {
  background: rgb(var(--danger-rgb) / 0.14);
  color: var(--danger);
  border-color: rgb(var(--danger-rgb) / 0.35);
}

.members h3 {
  color: var(--text);
  margin-bottom: 1rem;
}
.members-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.member-item {
  padding: 1rem;
  border-radius: var(--radius-lg);
  border: 1px solid rgb(var(--ink) / 0.08);
  background: linear-gradient(140deg, rgb(var(--ink) / 0.05), rgb(var(--ink) / 0.02));
}

.member-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.member-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-remove,
.btn-leave {
  padding: 0.55rem 1rem;
  border-radius: 10px;
  font-size: 0.9rem;
}

.member-item .role {
  display: block;
  color: var(--muted);
  font-size: 0.9rem;
  margin-top: 0.3rem;
}

.skills {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.skill-tag {
  background: rgb(var(--ink) / 0.06);
  padding: 0.3rem 0.6rem;
  border-radius: 4px;
  font-size: 0.85rem;
  color: var(--accent);
}

.error {
  color: var(--danger);
  text-align: center;
  padding: 2rem;
}

.apply-section {
  margin-top: 2rem;
  padding: 1.5rem;
  border-radius: var(--radius-lg);
  background: var(--glass);
  border: 1px solid rgb(var(--ink) / 0.12);
  box-shadow: var(--shadow-soft);
}

.btn-apply {
  width: 100%;
  padding: 0.9rem;
}

.btn-apply:disabled {
  cursor: not-allowed;
  opacity: 0.6;
  transform: none;
  box-shadow: none;
}

.apply-error {
  color: var(--danger);
  margin-top: 0.5rem;
  font-size: 0.9rem;
}

.apply-success {
  color: var(--accent-3);
  margin-top: 0.5rem;
  font-size: 0.9rem;
}

.member-status {
  margin-top: 2rem;
  padding: 1rem;
  border-radius: var(--radius-lg);
  background: rgba(83, 243, 197, 0.08);
  border: 1px solid rgba(83, 243, 197, 0.18);
  text-align: center;
}

.member-message {
  color: var(--accent);
  margin: 0;
  font-weight: 600;
}

.team-full-message {
  margin-top: 2rem;
  padding: 1rem;
  background: rgba(255, 125, 226, 0.06);
  border: 1px solid rgba(255, 125, 226, 0.18);
  border-radius: var(--radius-lg);
  text-align: center;
}

.team-full-message p {
  color: var(--accent-2);
  margin: 0;
  font-weight: 600;
}

@media (min-width: 640px) {
  .detail-card {
    padding: 2rem;
  }
  .detail-card h1 {
    font-size: 2rem;
  }
}
</style>

