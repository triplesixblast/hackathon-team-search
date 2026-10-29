<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import apiClient from '../utils/api';
import HackathonsCard from './hackathons/HackathonsCard.vue';

const hackathons = ref<any[]>([]);
const myTeams = ref<any[]>([]);
const invitations = ref<any[]>([]);
const loading = ref(true);
const error = ref('');

async function loadDashboard() {
  loading.value = true;
  error.value = '';
  try {
    // Загружаем данные параллельно
    const [hackathonsRes, teamsRes, invitationsRes] = await Promise.all([
      apiClient.get('/api/hackathons').catch(() => ({ data: [] })),
      apiClient.get('/api/teams/my').catch(() => ({ data: [] })),
      apiClient.get('/api/invitations', { params: { status_filter: 'pending' } }).catch(() => ({ data: [] })),
    ]);

    hackathons.value = hackathonsRes.data || [];
    myTeams.value = teamsRes.data || [];
    invitations.value = invitationsRes.data || [];
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Ошибка загрузки данных';
  } finally {
    loading.value = false;
  }
}

const activeHackathons = computed(() => {
  return hackathons.value.filter(h => h.status === 'active');
});

const upcomingHackathons = computed(() => {
  return hackathons.value.filter(h => h.status === 'upcoming').slice(0, 3);
});

onMounted(loadDashboard);
</script>

<template>
  <div class="dashboard">
    <h1>Дайджест</h1>
    
    <div v-if="loading" class="loading">Загрузка...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    
    <div v-else class="dashboard-content">
      <!-- Приглашения -->
      <section v-if="invitations.length > 0" class="dashboard-section">
        <div class="section-header">
          <h2>Новые приглашения</h2>
          <router-link to="/invitations" class="view-all">Все приглашения →</router-link>
        </div>
        <div class="invitations-preview">
          <div v-for="invitation in invitations.slice(0, 3)" :key="invitation.id" class="invitation-item">
            <div class="invitation-info">
              <strong>{{ invitation.team?.name }}</strong>
              <span class="inviter">От: {{ invitation.sent_by?.full_name }}</span>
            </div>
            <router-link :to="`/invitations`" class="btn-view">Посмотреть</router-link>
          </div>
        </div>
      </section>

      <!-- Мои команды -->
      <section v-if="myTeams.length > 0" class="dashboard-section">
        <div class="section-header">
          <h2>Мои команды</h2>
          <router-link to="/team" class="view-all">Все команды →</router-link>
        </div>
        <div class="teams-preview">
          <div v-for="team in myTeams.slice(0, 3)" :key="team.id" class="team-item">
            <div class="team-info">
              <h3>{{ team.name }}</h3>
              <p class="hackathon-name">{{ team.hackathon_name }}</p>
            </div>
            <router-link :to="`/teams/${team.id}`" class="btn-view">Открыть</router-link>
          </div>
        </div>
      </section>

      <!-- Активные хакатоны -->
      <section v-if="activeHackathons.length > 0" class="dashboard-section">
        <div class="section-header">
          <h2>Активные хакатоны</h2>
          <router-link to="/hackathons" class="view-all">Все хакатоны →</router-link>
        </div>
        <div class="hackathons-grid">
          <HackathonsCard 
            v-for="hackathon in activeHackathons.slice(0, 3)" 
            :key="hackathon.id" 
            :hackathon="hackathon" 
          />
        </div>
      </section>

      <!-- Ближайшие хакатоны -->
      <section v-if="upcomingHackathons.length > 0" class="dashboard-section">
        <div class="section-header">
          <h2>Ближайшие хакатоны</h2>
          <router-link to="/hackathons" class="view-all">Все хакатоны →</router-link>
        </div>
        <div class="hackathons-grid">
          <HackathonsCard 
            v-for="hackathon in upcomingHackathons" 
            :key="hackathon.id" 
            :hackathon="hackathon" 
          />
        </div>
      </section>

      <!-- Пустое состояние -->
      <div v-if="!loading && invitations.length === 0 && myTeams.length === 0 && hackathons.length === 0" class="empty-state">
        <p>Пока нет активности. Начните с просмотра доступных хакатонов!</p>
        <router-link to="/hackathons" class="btn-primary">Посмотреть хакатоны</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped lang="css">
.dashboard {
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
}
.dashboard h1 {
  color: var(--accent);
  margin-bottom: 2rem;
  font-size: 1.8rem;
}

.loading {
  text-align: center;
  padding: 3rem;
  color: var(--muted);
}

.error {
  color: var(--danger);
  text-align: center;
  padding: 2rem;
  background: var(--glass-strong);
  border-radius: 12px;
}

.dashboard-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.dashboard-section {
  background: var(--glass);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-soft);
  backdrop-filter: blur(var(--blur-soft)) saturate(1.4);
  -webkit-backdrop-filter: blur(var(--blur-soft)) saturate(1.4);
  border-radius: 12px;
  padding: 1.5rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}
.section-header h2 {
  color: var(--accent);
  font-size: 1.3rem;
  margin: 0;
}

.view-all {
  color: var(--muted);
  text-decoration: none;
  font-size: 0.9rem;
  transition: color 0.2s;
}
.view-all:hover {
  color: var(--accent);
}

.invitations-preview,
.teams-preview {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.invitation-item,
.team-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: var(--glass-strong);
  border-radius: 8px;
  gap: 1rem;
}

.invitation-info,
.team-info {
  flex: 1;
}
.invitation-info strong,
.team-info h3 {
  color: var(--text);
  display: block;
  margin-bottom: 0.3rem;
}

.inviter,
.hackathon-name {
  color: var(--muted);
  font-size: 0.9rem;
}

.hackathons-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}

.empty-state {
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
.empty-state p {
  margin-bottom: 1.5rem;
  font-size: 1.1rem;
}

.btn-view {
  white-space: nowrap;
}

@media (min-width: 640px) {
  .dashboard h1 {
    font-size: 2.2rem;
  }

  .hackathons-grid {
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1.5rem;
  }

  .dashboard-section {
    padding: 2rem;
  }
}
</style>

