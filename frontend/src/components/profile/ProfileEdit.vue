<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import apiClient from '../../utils/api';

const router = useRouter();

const form = ref({
  full_name: '',
  bio: '',
  skills: [] as string[],
  role_preference: '',
  experience_level: 'junior',
});

const newSkill = ref('');
const loading = ref(false);
const saving = ref(false);
const error = ref('');

// Состояния для кастомных dropdown
const experienceDropdownOpen = ref(false);
const roleDropdownOpen = ref(false);

const availableLevels = ['junior', 'middle', 'senior'];
const availableRoles = ['frontend', 'backend', 'fullstack', 'designer', 'product manager'];

async function loadProfile() {
  loading.value = true;
  error.value = '';
  try {
    const response = await apiClient.get('/api/users/me');
    const profile = response.data;
    form.value.full_name = profile.full_name;
    form.value.bio = profile.bio || '';
    form.value.skills = profile.skills || [];
    form.value.role_preference = profile.role_preference || '';
    form.value.experience_level = profile.experience_level;
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Ошибка';
  } finally {
    loading.value = false;
  }
}

function addSkill() {
  if (newSkill.value.trim() && !form.value.skills.includes(newSkill.value.trim())) {
    form.value.skills.push(newSkill.value.trim());
    newSkill.value = '';
  }
}

function removeSkill(skill: string) {
  form.value.skills = form.value.skills.filter(s => s !== skill);
}

function selectExperience(level: string) {
  form.value.experience_level = level;
  experienceDropdownOpen.value = false;
}

function selectRole(role: string) {
  form.value.role_preference = role;
  roleDropdownOpen.value = false;
}

// Закрываем dropdown при клике вне его
function handleClickOutside(event: MouseEvent) {
  const target = event.target as HTMLElement;
  if (!target.closest('.dropdown-wrapper')) {
    experienceDropdownOpen.value = false;
    roleDropdownOpen.value = false;
  }
}

async function save() {
  saving.value = true;
  error.value = '';
  try {
    await apiClient.put('/api/users/me', form.value);
    // Перенаправляем на страницу профиля после успешного сохранения
    router.push('/profile');
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Ошибка';
  } finally {
    saving.value = false;
  }
}

onMounted(() => {
  loadProfile();
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<template>
  <div class="profile-edit">
    <h2>Редактировать профиль</h2>
    <div v-if="loading">Загрузка...</div>
    <form v-else @submit.prevent="save">
      <div class="form-group">
        <label>Имя *</label>
        <input v-model="form.full_name" type="text" required />
      </div>
      <div class="form-group">
        <label>О себе</label>
        <textarea v-model="form.bio" rows="4"></textarea>
      </div>
      <div class="form-group dropdown-wrapper">
        <label>Опыт</label>
        <div class="custom-dropdown" @click.stop="experienceDropdownOpen = !experienceDropdownOpen">
          <span class="dropdown-value">{{ form.experience_level || 'Выберите уровень' }}</span>
          <svg class="dropdown-arrow" :class="{ open: experienceDropdownOpen }" width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M6 9L1 4h10L6 9z" fill="currentColor"/>
          </svg>
        </div>
        <div v-if="experienceDropdownOpen" class="dropdown-menu">
          <div 
            v-for="level in availableLevels" 
            :key="level" 
            class="dropdown-option" 
            :class="{ active: form.experience_level === level }"
            @click="selectExperience(level)"
          >
            {{ level }}
          </div>
        </div>
      </div>
      <div class="form-group dropdown-wrapper">
        <label>Роль</label>
        <div class="custom-dropdown" @click.stop="roleDropdownOpen = !roleDropdownOpen">
          <span class="dropdown-value">{{ form.role_preference || 'Не указано' }}</span>
          <svg class="dropdown-arrow" :class="{ open: roleDropdownOpen }" width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M6 9L1 4h10L6 9z" fill="currentColor"/>
          </svg>
        </div>
        <div v-if="roleDropdownOpen" class="dropdown-menu">
          <div class="dropdown-option" :class="{ active: !form.role_preference }" @click="selectRole('')">
            Не указано
          </div>
          <div 
            v-for="role in availableRoles" 
            :key="role" 
            class="dropdown-option" 
            :class="{ active: form.role_preference === role }"
            @click="selectRole(role)"
          >
            {{ role }}
          </div>
        </div>
      </div>
      <div class="form-group">
        <label>Навыки</label>
        <div class="skills-input">
          <input v-model="newSkill" type="text" placeholder="Добавить навык" @keyup.enter.prevent="addSkill" />
          <button type="button" class="btn-primary" @click="addSkill">Добавить</button>
        </div>
        <div class="skills-list">
          <span v-for="skill in form.skills" :key="skill" class="skill-tag">
            {{ skill }}
            <button type="button" @click="removeSkill(skill)" class="remove-skill">×</button>
          </span>
        </div>
      </div>
      <div v-if="error" class="error">{{ error }}</div>
      <button type="submit" :disabled="saving" class="btn-save btn-primary">Сохранить</button>
    </form>
  </div>
</template>

<style scoped lang="css">
.profile-edit {
  max-width: 600px;
  width: 100%;
  margin: 0 auto;
  background: var(--glass);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-soft);
  backdrop-filter: blur(var(--blur-soft)) saturate(1.4);
  -webkit-backdrop-filter: blur(var(--blur-soft)) saturate(1.4);
  border-radius: 12px;
  padding: 1.5rem;
  color: var(--text);
}
.profile-edit h2 {
  color: var(--accent);
  margin-bottom: 1.5rem;
}

.form-group {
  margin-bottom: 1.5rem;
}
.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: var(--muted);
}
.form-group input,
.form-group textarea {
  width: 100%;
  padding: 0.75rem 1rem;
  border-radius: 14px;
  border: 1px solid rgb(var(--ink) / 0.18);
  background: rgb(var(--ink) / 0.08);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  color: var(--text);
  font-size: 0.95rem;
  font-family: inherit;
  transition: all 0.2s ease;
  box-shadow: 0 4px 12px rgb(var(--shade) / 0.15);
}

.form-group input::placeholder {
  color: rgb(var(--ink) / 0.5);
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: rgb(var(--accent-rgb) / 0.5);
  background: rgb(var(--ink) / 0.12);
  box-shadow: 0 6px 20px rgb(var(--accent-rgb) / 0.2), 0 0 0 3px rgb(var(--accent-rgb) / 0.1);
}

.form-group textarea {
  resize: vertical;
  min-height: 100px;
}

.dropdown-wrapper {
  position: relative;
}

.custom-dropdown {
  width: 100%;
  padding: 0.75rem 1rem;
  padding-right: 2.5rem;
  border-radius: 14px;
  border: 1px solid rgb(var(--ink) / 0.18);
  background: rgb(var(--ink) / 0.08);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  color: var(--text);
  font-size: 0.95rem;
  font-family: inherit;
  transition: all 0.2s ease;
  box-shadow: 0 4px 12px rgb(var(--shade) / 0.15);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: relative;
}

.custom-dropdown:hover {
  border-color: rgb(var(--accent-rgb) / 0.4);
  background: rgb(var(--ink) / 0.1);
}

.dropdown-value {
  flex: 1;
  color: var(--text);
}

.dropdown-arrow {
  position: absolute;
  right: 0.75rem;
  color: rgb(var(--ink) / 0.7);
  transition: transform 0.2s ease;
  pointer-events: none;
}

.dropdown-arrow.open {
  transform: rotate(180deg);
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 0.5rem);
  left: 0;
  right: 0;
  z-index: 100;
  background: var(--menu-bg);
  border: 1px solid rgb(var(--ink) / 0.25);
  border-radius: var(--radius-sm);
  box-shadow: 0 20px 60px rgb(var(--shade) / 0.5), 0 0 0 1px rgb(var(--ink) / 0.08) inset;
  overflow-y: auto;
  overflow-x: hidden;
  max-height: 300px;
  animation: dropdownFadeIn 0.2s ease;
}

/* Стилизация скроллбара для dropdown */
.dropdown-menu::-webkit-scrollbar {
  width: 6px;
}

.dropdown-menu::-webkit-scrollbar-track {
  background: rgb(var(--ink) / 0.05);
  border-radius: 10px;
}

.dropdown-menu::-webkit-scrollbar-thumb {
  background: rgb(var(--accent-rgb) / 0.4);
  border-radius: 10px;
  transition: background 0.2s ease;
}

.dropdown-menu::-webkit-scrollbar-thumb:hover {
  background: rgb(var(--accent-rgb) / 0.6);
}

/* Для Firefox */
.dropdown-menu {
  scrollbar-width: thin;
  scrollbar-color: rgb(var(--accent-rgb) / 0.4) rgb(var(--ink) / 0.05);
}

@keyframes dropdownFadeIn {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.dropdown-option {
  padding: 0.75rem 1rem;
  color: var(--text);
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.15s ease;
  border-bottom: 1px solid rgb(var(--ink) / 0.05);
}

.dropdown-option:last-child {
  border-bottom: none;
}

.dropdown-option:hover {
  background: rgb(var(--ink) / 0.1);
  color: var(--accent);
}

.dropdown-option.active {
  background: rgb(var(--accent-rgb) / 0.2);
  color: var(--accent);
  font-weight: 600;
}

.skills-input {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  margin-bottom: 0.5rem;
  justify-content: space-between;
}
.skills-input input {
  flex: 1;
}
.skills-input button {
  white-space: nowrap;
}

.skills-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.skill-tag {
  background: rgb(var(--ink) / 0.06);
  padding: 0.4rem 0.8rem;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  border: 1px solid rgba(154, 231, 255, 0.2);
  color: var(--accent);
}

.remove-skill {
  background: transparent;
  border: none;
  color: var(--danger);
  cursor: pointer;
  font-size: 1.2rem;
  padding: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-save {
  width: 100%;
  margin-top: 1rem;
}
.btn-save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.error {
  color: var(--danger);
  margin-bottom: 1rem;
}

@media (min-width: 640px) {
  .profile-edit {
    padding: 2rem;
  }

  .skills-input {
    flex-direction: row;
  }
} 
</style>

