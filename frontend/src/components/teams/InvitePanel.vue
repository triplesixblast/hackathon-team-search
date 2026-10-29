<script setup lang="ts">
import { toast } from '../../composables/useFeedback';
import { ref, onMounted, onUnmounted, watch } from 'vue';
import apiClient from '../../utils/api';

const props = defineProps<{
  teamId: number | string;
  hackathonId: number | string;
}>();

const emit = defineEmits<{
  (e: 'invite-sent'): void;
}>();

const participants = ref<any[]>([]);
const loading = ref(false);
const error = ref('');
const inviting = ref<number | null>(null);

// Фильтры
const searchQuery = ref('');
const roleFilter = ref('');
const experienceFilter = ref('');
const skillFilter = ref('');

const availableRoles = ['frontend', 'backend', 'fullstack', 'designer', 'product manager'];
const availableLevels = ['junior', 'middle', 'senior'];
const availableSkills = ref<string[]>([]);

// Состояния для кастомных dropdown
const roleDropdownOpen = ref(false);
const experienceDropdownOpen = ref(false);

async function loadParticipants() {
  loading.value = true;
  error.value = '';
  try {
    const hackathonId = typeof props.hackathonId === 'string' 
      ? parseInt(props.hackathonId, 10) 
      : props.hackathonId;
    
    const params: any = {};
    if (searchQuery.value) params.search = searchQuery.value;
    if (roleFilter.value) params.role_preference = roleFilter.value;
    if (experienceFilter.value) params.experience_level = experienceFilter.value;
    if (skillFilter.value) params.skill = skillFilter.value;
    
    const response = await apiClient.get(`/api/users/hackathons/${hackathonId}/participants`, { params });
    participants.value = response.data;
    
    // Собираем уникальные навыки для фильтра
    const skillsSet = new Set<string>();
    response.data.forEach((p: any) => {
      if (p.skills && Array.isArray(p.skills)) {
        p.skills.forEach((s: string) => skillsSet.add(s));
      }
    });
    availableSkills.value = Array.from(skillsSet).sort();
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Ошибка';
  } finally {
    loading.value = false;
  }
}

// Debounce функция
let debounceTimer: ReturnType<typeof setTimeout> | null = null;

// Перезагружаем при изменении фильтров с debounce
watch([searchQuery, roleFilter, experienceFilter, skillFilter], () => {
  if (debounceTimer) {
    clearTimeout(debounceTimer);
  }
  debounceTimer = setTimeout(() => {
    loadParticipants();
  }, 300);
});

function clearFilters() {
  searchQuery.value = '';
  roleFilter.value = '';
  experienceFilter.value = '';
  skillFilter.value = '';
  roleDropdownOpen.value = false;
  experienceDropdownOpen.value = false;
}

function selectRole(role: string) {
  roleFilter.value = role;
  roleDropdownOpen.value = false;
}

function selectExperience(level: string) {
  experienceFilter.value = level;
  experienceDropdownOpen.value = false;
}

// Закрываем dropdown при клике вне его
function handleClickOutside(event: MouseEvent) {
  const target = event.target as HTMLElement;
  if (!target.closest('.dropdown-wrapper')) {
    roleDropdownOpen.value = false;
    experienceDropdownOpen.value = false;
  }
}

onMounted(() => {
  loadParticipants();
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});

async function inviteUser(userId: number) {
  inviting.value = userId;
  try {
    const teamId = typeof props.teamId === 'string' 
      ? parseInt(props.teamId, 10) 
      : props.teamId;
    await apiClient.post(`/api/teams/${teamId}/invite`, null, {
      params: { user_id: userId },
    });
    toast.success('Приглашение отправлено!');
    emit('invite-sent');
  } catch (e: any) {
    toast.error(e?.response?.data?.detail || e?.message || 'Ошибка');
  } finally {
    inviting.value = null;
  }
}

</script>

<template>
  <div class="invite-panel">
    <h3>Пригласить участников</h3>
    
    <!-- Фильтры -->
    <div class="filters">
      <div class="filter-group">
        <input 
          v-model="searchQuery" 
          type="text" 
          placeholder="Поиск по имени..." 
          class="filter-input"
        />
      </div>
      <div class="filter-group dropdown-wrapper">
        <div class="custom-dropdown" @click.stop="roleDropdownOpen = !roleDropdownOpen">
          <span class="dropdown-value">{{ roleFilter || 'Все роли' }}</span>
          <svg class="dropdown-arrow" :class="{ open: roleDropdownOpen }" width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M6 9L1 4h10L6 9z" fill="currentColor"/>
          </svg>
        </div>
        <div v-if="roleDropdownOpen" class="dropdown-menu">
          <div class="dropdown-option" :class="{ active: !roleFilter }" @click="selectRole('')">
            Все роли
          </div>
          <div 
            v-for="role in availableRoles" 
            :key="role" 
            class="dropdown-option" 
            :class="{ active: roleFilter === role }"
            @click="selectRole(role)"
          >
            {{ role }}
          </div>
        </div>
      </div>
      <div class="filter-group dropdown-wrapper">
        <div class="custom-dropdown" @click.stop="experienceDropdownOpen = !experienceDropdownOpen">
          <span class="dropdown-value">{{ experienceFilter || 'Все уровни' }}</span>
          <svg class="dropdown-arrow" :class="{ open: experienceDropdownOpen }" width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M6 9L1 4h10L6 9z" fill="currentColor"/>
          </svg>
        </div>
        <div v-if="experienceDropdownOpen" class="dropdown-menu">
          <div class="dropdown-option" :class="{ active: !experienceFilter }" @click="selectExperience('')">
            Все уровни
          </div>
          <div 
            v-for="level in availableLevels" 
            :key="level" 
            class="dropdown-option" 
            :class="{ active: experienceFilter === level }"
            @click="selectExperience(level)"
          >
            {{ level }}
          </div>
        </div>
      </div>
      <!-- <div class="filter-group">
        <select v-model="skillFilter" class="filter-select">
          <option value="">Все навыки</option>
          <option v-for="skill in availableSkills" :key="skill" :value="skill">{{ skill }}</option>
        </select>
      </div> -->
      <button @click="clearFilters" class="btn-clear-filters btn-ghost">Очистить</button>
    </div>
    
    <div v-if="loading">Загрузка...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="participants.length === 0" class="empty">Нет доступных участников</div>
    <div v-else class="participants-list">
      <div v-for="participant in participants" :key="participant.id" class="participant-card">
        <div class="participant-info">
          <strong>{{ participant.full_name }}</strong>
          <span v-if="participant.role_preference" class="role">{{ participant.role_preference }}</span>
          <div v-if="participant.skills && participant.skills.length > 0" class="skills">
            <span v-for="skill in participant.skills" :key="skill" class="skill-tag">{{ skill }}</span>
          </div>
        </div>
        <button
          @click="inviteUser(participant.id)"
          :disabled="inviting === participant.id"
          class="btn-invite btn-primary"
        >
          {{ inviting === participant.id ? 'Отправка...' : 'Пригласить' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped lang="css">
.invite-panel {
  margin-top: 2rem;
  padding: 1.6rem;
  border-radius: var(--radius-lg);
  background: var(--glass);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-soft);
  backdrop-filter: blur(var(--blur-soft));
  -webkit-backdrop-filter: blur(var(--blur-soft));
  position: relative;
  overflow: visible;
}
.invite-panel h3 {
  color: var(--text);
  margin-bottom: 1.2rem;
  font-size: 1.2rem;
}

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  align-items: stretch;
  margin-bottom: 1.5rem;
  padding: 0.9rem;
  background: rgb(var(--ink) / 0.03);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  position: relative;
  overflow: visible;
}

.filter-group {
  position: relative;
  display: flex;
  flex: 0 0 100%;
  min-width: 0;
}

.filter-input,
.custom-dropdown {
  width: 100%;
  height: 44px;
  padding: 0 1rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--hairline);
  background: var(--glass-strong);
  color: var(--text);
  font-size: 0.95rem;
  font-family: inherit;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.filter-input::placeholder {
  color: var(--muted);
}

.filter-input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgb(var(--accent-rgb) / 0.25);
}

.dropdown-wrapper {
  z-index: 10;
}

.custom-dropdown {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding-right: 0.9rem;
  cursor: pointer;
  user-select: none;
}

.custom-dropdown:hover {
  border-color: rgb(var(--accent-rgb) / 0.55);
}

.dropdown-value {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dropdown-arrow {
  flex: none;
  color: var(--muted);
  transition: transform 0.2s ease;
  pointer-events: none;
}

.dropdown-arrow.open {
  transform: rotate(180deg);
  color: var(--accent);
}

/* Меню плавающее, поэтому здесь стекло */
.dropdown-menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  min-width: 100%;
  z-index: 1000;
  padding: 4px;
  max-height: 240px;
  overflow-y: auto;
  overflow-x: hidden;
  background: var(--menu-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-strong);
  animation: dropdownFadeIn 0.18s ease;
  scrollbar-width: thin;
  scrollbar-color: rgb(var(--accent-rgb) / 0.5) transparent;
}

.dropdown-menu::-webkit-scrollbar {
  width: 6px;
}
.dropdown-menu::-webkit-scrollbar-thumb {
  background: rgb(var(--accent-rgb) / 0.5);
  border-radius: 6px;
}

@keyframes dropdownFadeIn {
  from {
    opacity: 0;
    transform: translateY(-6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.dropdown-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.55rem 0.75rem;
  margin: 1px 0;
  border-radius: 8px;
  color: var(--text);
  font-size: 0.92rem;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.dropdown-option:hover {
  background: rgb(var(--ink) / 0.08);
}

.dropdown-option.active {
  color: var(--accent);
  font-weight: 600;
}

.dropdown-option.active::after {
  content: '';
  flex: none;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
}

.btn-clear-filters {
  flex: 0 0 100%;
  height: 44px;
  min-height: 44px;
  padding: 0 1.1rem;
  font-size: 0.9rem;
  white-space: nowrap;
  background: transparent;
  color: var(--muted);
  border: 1px solid var(--hairline);
}

.btn-clear-filters:hover {
  color: var(--text);
  border-color: var(--accent);
}

@media (min-width: 640px) {
  .filters {
    flex-wrap: nowrap;
  }
  .filter-group {
    flex: 0 0 150px;
  }
  .filter-group:first-child {
    flex: 1 1 0;
    min-width: 140px;
  }
  .btn-clear-filters {
    flex: 0 0 auto;
  }
}

.participants-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.participant-card {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  background: linear-gradient(140deg, rgb(var(--ink) / 0.05), rgb(var(--ink) / 0.02));
  padding: 1rem;
  border-radius: var(--radius-lg);
  border: 1px solid rgb(var(--ink) / 0.08);
  backdrop-filter: blur(var(--blur-soft));
  -webkit-backdrop-filter: blur(var(--blur-soft));
}

.participant-info {
  flex: 1;
  width: 100%;
}
.participant-info strong {
  color: var(--text);
  display: block;
  margin-bottom: 0.3rem;
}
.participant-info .role {
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
  border-radius: 6px;
  font-size: 0.85rem;
  color: var(--accent);
  border: 1px solid rgba(154, 231, 255, 0.2);
}

.btn-invite {
  width: 100%;
  padding: 0.7rem 1.2rem;
  border-radius: 12px;
  font-size: 0.95rem;
}
.btn-invite:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.error {
  color: var(--danger);
}

.empty {
  color: var(--muted);
  text-align: center;
  padding: 2rem;
}

@media (min-width: 640px) {
  .participant-card {
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
    gap: 0;
  }
  .btn-invite {
    width: auto;
  }
}
</style>

