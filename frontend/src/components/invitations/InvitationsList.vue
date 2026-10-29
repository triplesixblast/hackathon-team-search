<script setup lang="ts">
import { toast } from '../../composables/useFeedback';
import { ref, onMounted, onUnmounted, computed, watch } from 'vue';
import { useRoute } from 'vue-router';
import apiClient from '../../utils/api';

const route = useRoute();
const invitations = ref<any[]>([]);
const applications = ref<any[]>([]);
const loading = ref(false);
const error = ref('');
const respondedNotifications = ref<Set<number>>(new Set());
const viewedNotifications = ref<Set<number>>(new Set());

// Загружаем просмотренные уведомления из localStorage
function loadViewedNotifications() {
  try {
    const viewed = localStorage.getItem('viewedNotifications');
    if (viewed) {
      viewedNotifications.value = new Set(JSON.parse(viewed));
    }
  } catch (e) {
    console.error('Failed to load viewed notifications:', e);
  }
}

// Сохраняем просмотренные уведомления в localStorage
function saveViewedNotifications() {
  try {
    localStorage.setItem('viewedNotifications', JSON.stringify(Array.from(viewedNotifications.value)));
  } catch (e) {
    console.error('Failed to save viewed notifications:', e);
  }
}

// Отмечаем все уведомления как просмотренные
function markAllAsViewed() {
  allNotifications.value.forEach(notif => {
    if (notif.status === 'pending') {
      viewedNotifications.value.add(notif.id);
    }
  });
  saveViewedNotifications();
  // Обновляем счетчик в родительском компоненте
  window.dispatchEvent(new CustomEvent('notifications-viewed'));
}

async function loadInvitations() {
  loading.value = true;
  error.value = '';
  try {
    // Загружаем приглашения и результаты заявок (для обычных пользователей)
    const invitationsResponse = await apiClient.get('/api/invitations', {
      params: { status_filter: 'pending' },
    });
    invitations.value = invitationsResponse.data;
    
    // Загружаем заявки на вступление в мои команды (для капитана)
    try {
      const applicationsResponse = await apiClient.get('/api/invitations/applications');
      applications.value = applicationsResponse.data;
    } catch (e: any) {
      // Если нет заявок или пользователь не капитан, это нормально
      applications.value = [];
    }
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Ошибка';
  } finally {
    loading.value = false;
  }
}

async function respondToInvitation(invitationId: number, accept: boolean) {
  // Сразу отмечаем как обработанное, чтобы скрыть кнопки
  respondedNotifications.value.add(invitationId);
  // Отмечаем как просмотренное
  viewedNotifications.value.add(invitationId);
  saveViewedNotifications();
  
  // Удаляем уведомление из списка сразу
  invitations.value = invitations.value.filter(inv => inv.id !== invitationId);
  
  try {
    await apiClient.post(`/api/invitations/${invitationId}/accept`, {
      accept
    });
    toast.success(accept ? 'Приглашение принято!' : 'Приглашение отклонено');
    // Обновляем счетчик
    window.dispatchEvent(new CustomEvent('notifications-updated'));
  } catch (e: any) {
    // В случае ошибки возвращаем уведомление в список и убираем из обработанных
    loadInvitations();
    respondedNotifications.value.delete(invitationId);
    viewedNotifications.value.delete(invitationId);
    toast.error(e?.response?.data?.detail || e?.message || 'Ошибка');
  }
}

async function respondToApplication(invitationId: number, accept: boolean) {
  // Сразу отмечаем как обработанное, чтобы скрыть кнопки
  respondedNotifications.value.add(invitationId);
  // Отмечаем как просмотренное
  viewedNotifications.value.add(invitationId);
  saveViewedNotifications();
  
  // Удаляем уведомление из списка сразу
  applications.value = applications.value.filter(app => app.id !== invitationId);
  
  try {
    if (accept) {
      await apiClient.post(`/api/invitations/${invitationId}/approve`);
      toast.success('Заявка принята!');
    } else {
      await apiClient.post(`/api/invitations/${invitationId}/reject`);
      toast.success('Заявка отклонена');
    }
    // Обновляем счетчик
    window.dispatchEvent(new CustomEvent('notifications-updated'));
  } catch (e: any) {
    // В случае ошибки возвращаем уведомление в список и убираем из обработанных
    loadInvitations();
    respondedNotifications.value.delete(invitationId);
    viewedNotifications.value.delete(invitationId);
    toast.error(e?.response?.data?.detail || e?.message || 'Ошибка');
  }
}

const allNotifications = computed(() => {
  const result: any[] = [];
  
  // Добавляем приглашения и результаты заявок
  invitations.value.forEach(inv => {
    // Результат собственной заявки: kind приходит с бэкенда
    const isApplicationResult = inv.kind === 'application' && inv.status !== 'pending';
    
    if (isApplicationResult) {
      result.push({
        ...inv,
        type: 'application_result'
      });
    } else {
      result.push({
        ...inv,
        type: 'invitation'
      });
    }
  });
  
  // Добавляем заявки (только pending для капитана)
  applications.value.forEach(app => {
    result.push({
      ...app,
      type: 'application'
    });
  });
  
  // Сортируем по дате: для результатов заявок используем responded_at, для остальных - created_at
  return result.sort((a, b) => {
    const dateA = a.responded_at ? new Date(a.responded_at).getTime() : new Date(a.created_at).getTime();
    const dateB = b.responded_at ? new Date(b.responded_at).getTime() : new Date(b.created_at).getTime();
    return dateB - dateA;
  });
});

// Отслеживаем переход на страницу уведомлений
watch(() => route.path, (newPath) => {
  if (newPath === '/invitations') {
    // Когда пользователь заходит на страницу уведомлений, отмечаем все как просмотренные
    setTimeout(() => {
      markAllAsViewed();
    }, 500); // Небольшая задержка, чтобы уведомления успели загрузиться
  }
}, { immediate: true });

let viewedTimer: ReturnType<typeof setTimeout> | undefined;

onMounted(() => {
  loadViewedNotifications();
  loadInvitations();
  
  // Слушаем события обновления уведомлений
  window.addEventListener('notifications-updated', loadInvitations);
  
  // Отмечаем все уведомления как просмотренные при монтировании
  viewedTimer = setTimeout(() => {
    markAllAsViewed();
  }, 1000);
});

onUnmounted(() => {
  clearTimeout(viewedTimer);
  window.removeEventListener('notifications-updated', loadInvitations);
});
</script>

<template>
  <div class="invitations-list">
    <h1>Уведомления</h1>
    <div v-if="loading">Загрузка...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="allNotifications.length === 0" class="empty">Нет уведомлений</div>
    <div v-else class="notifications-grid">
      <!-- Приглашения (для обычных пользователей) -->
      <div v-for="notification in allNotifications" :key="notification.id" class="notification-card">
        <div v-if="notification.type === 'invitation'" class="invitation-notification">
          <div class="notification-header">
            <h3>Приглашение в команду: {{ notification.team?.name }}</h3>
            <span class="notification-type-badge invitation-badge">Приглашение</span>
          </div>
          <p v-if="notification.team?.description" class="description">{{ notification.team.description }}</p>
          <div class="inviter">
            <strong>От:</strong> {{ notification.sent_by?.full_name }}
          </div>
          <div v-if="!respondedNotifications.has(notification.id) && notification.status === 'pending'" class="actions">
            <button @click="respondToInvitation(notification.id, true)" class="btn-accept">Принять</button>
            <button @click="respondToInvitation(notification.id, false)" class="btn-decline">Отклонить</button>
          </div>
          <div v-else-if="notification.status !== 'pending'" class="status-message">
            <p v-if="notification.status === 'accepted'" class="accepted-message">Приглашение принято</p>
            <p v-else-if="notification.status === 'declined'" class="declined-message">Приглашение отклонено</p>
          </div>
        </div>
        
        <!-- Заявки на вступление (для капитана) -->
        <div v-else-if="notification.type === 'application'" class="application-notification">
          <div class="notification-header">
            <h3>Заявка на вступление в команду: {{ notification.team?.name }}</h3>
            <span class="notification-type-badge application-badge">Заявка</span>
          </div>
          <p v-if="notification.team?.description" class="description">{{ notification.team.description }}</p>
          <div class="applicant">
            <strong>Пользователь:</strong> {{ notification.user?.full_name }}
            <span v-if="notification.user?.role_preference" class="role">({{ notification.user.role_preference }})</span>
          </div>
          <div v-if="notification.user?.skills && notification.user.skills.length > 0" class="applicant-skills">
            <strong>Навыки:</strong>
            <div class="skills-list">
              <span v-for="skill in notification.user.skills" :key="skill" class="skill-tag">{{ skill }}</span>
            </div>
          </div>
          <div v-if="!respondedNotifications.has(notification.id) && notification.status === 'pending'" class="actions">
            <button @click="respondToApplication(notification.id, true)" class="btn-accept">Принять</button>
            <button @click="respondToApplication(notification.id, false)" class="btn-decline">Отклонить</button>
          </div>
          <div v-else-if="notification.status !== 'pending'" class="status-message">
            <p v-if="notification.status === 'accepted'" class="accepted-message">Заявка принята</p>
            <p v-else-if="notification.status === 'declined'" class="declined-message">Заявка отклонена</p>
          </div>
        </div>
        
        <!-- Результаты заявок (для пользователя) -->
        <div v-else-if="notification.type === 'application_result'" class="application-result-notification">
          <div class="notification-header">
            <h3>Результат заявки в команду: {{ notification.team?.name }}</h3>
            <span v-if="notification.status === 'accepted'" class="notification-type-badge accepted-badge">Принято</span>
            <span v-else-if="notification.status === 'declined'" class="notification-type-badge declined-badge">Отклонено</span>
          </div>
          <p v-if="notification.team?.description" class="description">{{ notification.team.description }}</p>
          <div class="result-message">
            <p v-if="notification.status === 'accepted'" class="accepted-message">
              Ваша заявка была принята! Вы теперь участник команды.
            </p>
            <p v-else-if="notification.status === 'declined'" class="declined-message">
              Ваша заявка была отклонена капитаном команды.
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="css">
.invitations-list {
  max-width: 800px;
  margin: 0 auto;
}
.invitations-list h1 {
  color: var(--accent);
  margin-bottom: 2rem;
}

.notifications-grid {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.notification-card {
  background: var(--glass);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-soft);
  backdrop-filter: blur(var(--blur-soft)) saturate(1.4);
  -webkit-backdrop-filter: blur(var(--blur-soft)) saturate(1.4);
  border-radius: 12px;
  padding: 1.5rem;
  color: var(--text);
}

.notification-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.5rem;
  margin-left: 1rem;
}

.notification-header h3 {
  color: var(--accent);
  margin: 0;
  flex: 1;
}

.notification-type-badge {
  padding: 0.3rem 0.8rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.invitation-badge {
  background: rgba(83, 243, 197, 0.16);
  color: var(--accent-3);
}

.application-badge {
  background: rgba(255, 200, 87, 0.16);
  color: #d98a00;
}

.accepted-badge {
  background: rgba(83, 243, 197, 0.16);
  color: var(--accent-3);
}

.declined-badge {
  background: rgb(var(--danger-rgb) / 0.16);
  color: var(--danger);
}

.application-result-notification {
  border-left: 4px solid var(--accent);
}

.result-message {
  margin: 1rem 0;
  padding: 1rem;
  border-radius: 6px;
}

.accepted-message {
  color: var(--accent-3);
  margin: 0;
  font-weight: 500;
}

.declined-message {
  color: var(--danger);
  margin: 0;
  font-weight: 500;
}

.status-message {
  margin-top: 1rem;
  padding: 0.8rem;
  border-radius: 6px;
  background: var(--glass-strong);
}

.status-message p {
  margin: 0;
  font-weight: 500;
}

.description {
  color: var(--muted);
  margin: 0.5rem 0;
}

.inviter,
.applicant {
  color: var(--muted);
  margin: 1rem 0;
}

.applicant .role {
  color: var(--accent);
  font-size: 0.9rem;
}

.applicant-skills {
  margin: 1rem 0;
  color: var(--muted);
}

.skills-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.skill-tag {
  background: var(--glass-strong);
  padding: 0.3rem 0.6rem;
  border-radius: 4px;
  font-size: 0.85rem;
  color: var(--accent);
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
  margin-top: 1rem;
}

.btn-accept,
.btn-decline {
  flex: 1;
  padding: 0.7rem;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  cursor: pointer;
}
.btn-accept {
  background: rgba(83, 243, 197, 0.16);
  color: var(--accent-3);
}
.btn-decline {
  background: rgb(var(--danger-rgb) / 0.16);
  color: var(--danger);
}

.error {
  color: var(--danger);
  text-align: center;
  padding: 2rem;
}

.empty {
  text-align: center;
  color: var(--muted);
  padding: 3rem;
  background: var(--glass);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-soft);
  backdrop-filter: blur(var(--blur-soft)) saturate(1.4);
  -webkit-backdrop-filter: blur(var(--blur-soft)) saturate(1.4);
  border-radius: 12px;
}

@media (min-width: 640px) {
  .actions {
    flex-direction: row;
    gap: 1rem;
  }
}
</style>
