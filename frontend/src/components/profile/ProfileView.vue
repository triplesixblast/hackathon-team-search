<script setup lang="ts">
import { ref, onMounted } from 'vue';
import apiClient from '../../utils/api';
import { logout } from '../../utils/auth';

const props = defineProps<{
  userId?: number;
}>();

const profile = ref<any>(null);
const loading = ref(false);
const error = ref('');

async function loadProfile() {
  loading.value = true;
  error.value = '';
  try {
    const url = props.userId
      ? `/api/users/${props.userId}`
      : '/api/users/me';
    const response = await apiClient.get(url);
    profile.value = response.data;
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Ошибка';
  } finally {
    loading.value = false;
  }
}

function handleLogout() {
  logout();
}

onMounted(loadProfile);
</script>

<template>
  <div class="profile-view">
    <div v-if="loading">Загрузка...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="profile" class="profile-card">
      <div class="profile-header">
        <div class="profile-info">
          <h2>{{ profile.full_name }}</h2>
          <p v-if="profile.telegram_username"> telegram: @{{ profile.telegram_username }}</p>
        </div>
      </div>
      <div v-if="profile.bio" class="bio">{{ profile.bio }}</div>
      <div class="profile-details">
        <div class="detail-item">
          <strong>Опыт:</strong> {{ profile.experience_level }}
        </div>
        <div v-if="profile.role_preference" class="detail-item">
          <strong>Роль:</strong> {{ profile.role_preference }}
        </div>
        <div v-if="profile.skills && profile.skills.length > 0" class="skills">
          <strong>Навыки:</strong>
          <div class="skills-list">
            <span v-for="skill in profile.skills" :key="skill" class="skill-tag">{{ skill }}</span>
          </div>
        </div>
      </div>
      <div class="profile-actions">
        <router-link to="/profile/edit" class="btn-edit btn-primary">Редактировать профиль</router-link>
        <button @click="handleLogout" class="btn-logout">Выйти из аккаунта</button>
      </div>
    </div>
  </div>
</template>

<style scoped lang="css">
.profile-view {
  max-width: 600px;
  width: 100%;
  margin: 0 auto;
}

.profile-card {
  background: var(--glass);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-soft);
  backdrop-filter: blur(var(--blur-soft)) saturate(1.4);
  -webkit-backdrop-filter: blur(var(--blur-soft)) saturate(1.4);
  border-radius: 12px;
  padding: 1.5rem;
  color: var(--text);
}

.profile-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  object-fit: cover;
}

.profile-info h2 {
  margin: 0;
  color: var(--accent);
}

.bio {
  margin-bottom: 1.5rem;
  color: var(--muted);
  line-height: 1.6;
}

.profile-details {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.detail-item {
  color: var(--text);
}

.skills {
  margin-top: 0.5rem;
}

.skills-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.skill-tag {
  background: var(--glass-strong);
  padding: 0.4rem 0.8rem;
  border-radius: 6px;
  font-size: 0.9rem;
  color: var(--accent);
}

.profile-actions {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
}
.btn-edit,
.btn-logout {
  width: 100%;
  text-align: center;
  font-size: 1rem;
  font-weight: 700;
}

.btn-logout {
  background: linear-gradient(135deg, var(--danger) 0%, var(--danger) 50%, var(--danger) 100%);
  color: var(--on-accent);
  box-shadow: 0 10px 30px rgba(255, 71, 87, 0.3), 0 8px 18px rgb(var(--shade) / 0.3);
  border: none;
  cursor: pointer;
  border-radius: 14px;
  padding: 0.9rem 1.25rem;
  transition: transform 0.2s ease, box-shadow 0.25s ease, background 0.2s ease;
  position: relative;
  isolation: isolate;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: inherit;
  letter-spacing: 0.01em;
  line-height: 1.15;
}

.btn-logout::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: radial-gradient(circle at 20% 20%, rgb(var(--ink) / 0.22), transparent 45%);
  opacity: 0;
  transition: opacity 0.25s ease;
  z-index: -1;
  pointer-events: none;
}

.btn-logout:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 35px rgba(255, 71, 87, 0.4), 0 10px 22px rgb(var(--shade) / 0.35);
}

.btn-logout:hover::after {
  opacity: 1;
}

.btn-logout:active {
  transform: translateY(0);
  box-shadow: 0 6px 20px rgba(255, 71, 87, 0.25), 0 4px 12px rgb(var(--shade) / 0.25);
}

.error {
  color: var(--danger);
  text-align: center;
  padding: 2rem;
}
@media (min-width: 640px) {
  .profile-card {
    padding: 2rem;
  }
  .profile-header {
    flex-direction: row;
    text-align: left;
    gap: 1.5rem;
  }
}
</style>

