<script setup lang="ts">
import { hackathonStatuses } from '../../utils/statusLabels';
import { ref, onMounted, onUnmounted, defineProps, defineEmits } from 'vue';
import { adminApiClient } from '../../utils/api';

const props = defineProps<{
  mode: 'create' | 'edit';
  hackathonId?: number;
}>();

const emit = defineEmits<{
  saved: [];
  cancelled: [];
}>();

const form = ref({
  name: '',
  description: '',
  start_date: '',
  end_date: '',
  max_team_size: 5,
  status: 'upcoming'
});

const loading = ref(false);
const error = ref('');
const validationErrors = ref<Record<string, string>>({});

// Состояние для кастомного dropdown статуса
const statusDropdownOpen = ref(false);
const availableStatuses = hackathonStatuses;

function selectStatus(status: string) {
  form.value.status = status;
  statusDropdownOpen.value = false;
}

// Закрываем dropdown при клике вне его
function handleClickOutside(event: MouseEvent) {
  const target = event.target as HTMLElement;
  if (!target.closest('.dropdown-wrapper')) {
    statusDropdownOpen.value = false;
  }
}

function formatDateTimeForInput(dateStr: string): string {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const hours = String(d.getHours()).padStart(2, '0');
  const minutes = String(d.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

async function loadHackathon() {
  if (props.mode !== 'edit' || !props.hackathonId) return;
  loading.value = true;
  error.value = '';
  try {
    const response = await adminApiClient.get('/api/admin/hackathons');
    const hackathon = response.data.find((h: any) => h.id === props.hackathonId);
    if (!hackathon) throw new Error('Хакатон не найден');
    form.value.name = hackathon.name;
    form.value.description = hackathon.description || '';
    form.value.start_date = formatDateTimeForInput(hackathon.start_date);
    form.value.end_date = formatDateTimeForInput(hackathon.end_date);
    form.value.max_team_size = hackathon.max_team_size;
    form.value.status = hackathon.status;
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Ошибка загрузки';
  } finally {
    loading.value = false;
  }
}

function validate(): boolean {
  validationErrors.value = {};
  if (!form.value.name.trim()) {
    validationErrors.value.name = 'Название обязательно';
  }
  if (!form.value.start_date) {
    validationErrors.value.start_date = 'Дата начала обязательна';
  }
  if (!form.value.end_date) {
    validationErrors.value.end_date = 'Дата окончания обязательна';
  }
  if (form.value.start_date && form.value.end_date) {
    if (new Date(form.value.end_date) <= new Date(form.value.start_date)) {
      validationErrors.value.end_date = 'Дата окончания должна быть позже даты начала';
    }
  }
  if (form.value.max_team_size < 1) {
    validationErrors.value.max_team_size = 'Размер команды должен быть >= 1';
  }
  return Object.keys(validationErrors.value).length === 0;
}

async function save() {
  if (!validate()) return;
  loading.value = true;
  error.value = '';
  try {
    const url = props.mode === 'create'
      ? '/api/hackathons'
      : `/api/hackathons/${props.hackathonId}`;
    const payload: any = {
      name: form.value.name,
      description: form.value.description || null,
      start_date: new Date(form.value.start_date).toISOString(),
      end_date: new Date(form.value.end_date).toISOString(),
      max_team_size: form.value.max_team_size,
    };
    if (props.mode === 'edit') {
      payload.status = form.value.status;
    }
    if (props.mode === 'create') {
      await adminApiClient.post(url, payload);
    } else {
      await adminApiClient.put(url, payload);
    }
    emit('saved');
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Ошибка сохранения';
  } finally {
    loading.value = false;
  }
}

function cancel() {
  emit('cancelled');
}

onMounted(() => {
  if (props.mode === 'edit') {
    loadHackathon();
  }
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<template>
  <div class="hackathon-edit-form">
    <h2>{{ props.mode === 'create' ? 'Создать хакатон' : 'Редактировать хакатон' }}</h2>
    <div v-if="loading && props.mode === 'edit'" class="loading">Загрузка...</div>
    <form v-else @submit.prevent="save">
      <div class="form-group">
        <label>Название *</label>
        <input v-model="form.name" type="text" required />
        <span v-if="validationErrors.name" class="error-text">{{ validationErrors.name }}</span>
      </div>
      <div class="form-group">
        <label>Описание</label>
        <textarea v-model="form.description" rows="4"></textarea>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Дата начала *</label>
          <input v-model="form.start_date" type="datetime-local" required />
          <span v-if="validationErrors.start_date" class="error-text">{{ validationErrors.start_date }}</span>
        </div>
        <div class="form-group">
          <label>Дата окончания *</label>
          <input v-model="form.end_date" type="datetime-local" required />
          <span v-if="validationErrors.end_date" class="error-text">{{ validationErrors.end_date }}</span>
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Максимальный размер команды</label>
          <input v-model.number="form.max_team_size" type="number" min="1" />
          <span v-if="validationErrors.max_team_size" class="error-text">{{ validationErrors.max_team_size }}</span>
        </div>
        <div v-if="props.mode === 'edit'" class="form-group dropdown-wrapper">
          <label>Статус</label>
          <div class="custom-dropdown" @click.stop="statusDropdownOpen = !statusDropdownOpen">
            <span class="dropdown-value">{{ availableStatuses.find(s => s.value === form.status)?.label || 'Выберите статус' }}</span>
            <svg class="dropdown-arrow" :class="{ open: statusDropdownOpen }" width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M6 9L1 4h10L6 9z" fill="currentColor"/>
            </svg>
          </div>
          <div v-if="statusDropdownOpen" class="dropdown-menu">
            <div 
              v-for="status in availableStatuses" 
              :key="status.value" 
              class="dropdown-option" 
              :class="{ active: form.status === status.value }"
              @click="selectStatus(status.value)"
            >
              {{ status.label }}
            </div>
          </div>
        </div>
      </div>
      <div v-if="error" class="error-message">{{ error }}</div>
      <div class="form-actions">
        <button type="submit" :disabled="loading" class="btn-primary">Сохранить</button>
        <button type="button" @click="cancel" class="btn-secondary">Отмена</button>
      </div>
    </form>
  </div>
</template>

<style scoped lang="css">
.hackathon-edit-form {
  max-width: 800px;
  width: 100%;
  margin: 1rem auto;
  padding: 1.5rem;
  background: var(--glass);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-soft);
  backdrop-filter: blur(var(--blur-soft)) saturate(1.4);
  -webkit-backdrop-filter: blur(var(--blur-soft)) saturate(1.4);
  border-radius: 12px;
  color: var(--text);
}
.hackathon-edit-form h2 {
  color: var(--accent);
  margin-bottom: 1.8rem;
}

.form-group {
  margin-bottom: 1.5rem;
}
.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
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

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}

.error-text {
  display: block;
  color: var(--danger);
  font-size: 0.9rem;
  margin-top: 0.3rem;
}

.error-message {
  background: rgb(var(--danger-rgb) / 0.14);
  color: var(--danger);
  padding: 0.8rem;
  border-radius: 6px;
  margin-bottom: 1rem;
}

.form-actions {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 2rem;
}

.btn-primary,
.btn-secondary {
  padding: 0.7rem 1.5rem;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.15s;
  width: 100%;
}

.btn-primary {
  background: var(--accent);
  color: var(--on-accent);
}
.btn-primary:hover:not(:disabled) {
  background: var(--grad);
}
.btn-primary:disabled {
  background: var(--glass-strong);
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--border);
  color: var(--text);
}
.btn-secondary:hover {
  background: var(--glass-strong);
}

.loading {
  text-align: center;
  padding: 2rem;
  color: var(--accent);
}

@media (min-width: 768px) {
  .hackathon-edit-form {
    margin: 2rem auto;
    padding: 2rem;
  }

  .form-row {
    grid-template-columns: 1fr;
  }
}

@media (min-width: 640px) {
  .form-actions {
    flex-direction: row;
  }

  .btn-primary,
  .btn-secondary {
    width: auto;
    padding: 0.7rem 1.8rem;
  }
}
</style>

