<script setup lang="ts">
import { translateApi } from '../../utils/apiMessages';
import { ref, onMounted, computed } from 'vue';
import { useTeamsStore } from '../../store/teams';
import apiClient from '../../utils/api';

const props = defineProps<{
  hackathonId: string | number;
}>();

const emit = defineEmits<{
  (e: 'team-created'): void;
  (e: 'cancel'): void;
}>();

const teamsStore = useTeamsStore();
const showForm = ref(false);
const teamName = ref('');
const teamDescription = ref('');
const creating = ref(false);
const error = ref('');
const canCreateError = ref('');
const canCreate = ref<boolean | null>(null);
const checking = ref(false);

// Проверяем, есть ли уже созданная команда
const hasExistingTeam = computed(() => {
  if (canCreate.value === false && canCreateError.value) {
    const errorLower = canCreateError.value.toLowerCase();
    return errorLower.includes('already created') || errorLower.includes('one user can create only one team');
  }
  return false;
});

// Преобразуем hackathonId в число
const hackathonIdNum = computed(() => {
  const id = typeof props.hackathonId === 'string' 
    ? parseInt(props.hackathonId, 10) 
    : props.hackathonId;
  if (isNaN(id)) {
    throw new Error('Invalid hackathon ID');
  }
  return id;
});

async function handleSubmit() {
  if (!teamName.value.trim()) {
    error.value = 'Название команды обязательно';
    return;
  }

  creating.value = true;
  error.value = '';

  try {
    await teamsStore.createTeam({
      hackathon_id: hackathonIdNum.value,
      name: teamName.value.trim(),
      description: teamDescription.value.trim() || undefined,
    });
    
    // Сброс формы
    teamName.value = '';
    teamDescription.value = '';
    showForm.value = false;
    
    // Обновляем проверку возможности создания
    await checkCanCreate();
    
    emit('team-created');
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Ошибка создания команды';
  } finally {
    creating.value = false;
  }
}

function handleCancel() {
  teamName.value = '';
  teamDescription.value = '';
  error.value = '';
  showForm.value = false;
  emit('cancel');
}

async function checkCanCreate() {
  checking.value = true;
  canCreateError.value = '';
  try {
    const response = await apiClient.get(`/api/teams/can-create/${hackathonIdNum.value}`);
    canCreate.value = response.data.can_create;
    if (!response.data.can_create && response.data.reason) {
      canCreateError.value = response.data.reason;
    }
  } catch (e: any) {
    // Если ошибка, разрешаем попытку создания (бэкенд проверит)
    canCreate.value = true;
  } finally {
    checking.value = false;
  }
}

onMounted(() => {
  checkCanCreate();
});
</script>

<template>
  <div class="create-team-form" v-if="!hasExistingTeam">
    <div v-if="checking" class="checking">Проверка...</div>
    <button 
      v-else-if="!showForm && canCreate !== false" 
      @click="showForm = true" 
      class="btn-create btn-primary"
    >
      Создать команду
    </button>
    <div v-else-if="canCreate === false && !showForm && canCreateError && !canCreateError.toLowerCase().includes('you must register') && !canCreateError.toLowerCase().includes('already created')" class="cannot-create">
      <span class="info-icon" aria-hidden="true">i</span>
      <p>{{ translateApi(canCreateError) || 'Вы не можете создать команду для этого хакатона' }}</p>
    </div>
    
    <div v-else class="form-container">
      <h3>Создать новую команду</h3>
      
      <div v-if="error" class="error-message">{{ error }}</div>
      
      <form @submit.prevent="handleSubmit" class="form">
        <div class="form-group">
          <label for="team-name">Название команды *</label>
          <input
            id="team-name"
            v-model="teamName"
            type="text"
            placeholder="Введите название команды"
            required
            :disabled="creating"
            class="input"
          />
        </div>
        
        <div class="form-group">
          <label for="team-description">Описание команды</label>
          <textarea
            id="team-description"
            v-model="teamDescription"
            placeholder="Расскажите о вашей команде (необязательно)"
            rows="4"
            :disabled="creating"
            class="textarea"
          ></textarea>
        </div>
        
        <div class="form-actions">
          <button type="submit" :disabled="creating || !teamName.trim()" class="btn-submit btn-primary">
            {{ creating ? 'Создание...' : 'Создать команду' }}
          </button>
          <button type="button" @click="handleCancel" :disabled="creating" class="btn-cancel btn-ghost">
            Отмена
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped lang="css">
.create-team-form {
  margin-bottom: 2rem;
}

.btn-create {
  padding: 0.8rem 1.5rem;
}

.form-container {
  background: var(--glass);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-soft);
  backdrop-filter: blur(var(--blur-soft)) saturate(1.4);
  -webkit-backdrop-filter: blur(var(--blur-soft)) saturate(1.4);
  border-radius: 12px;
  padding: 1.5rem;
  color: var(--text);
}
.form-container h3 {
  color: var(--accent);
  margin: 0 0 1.5rem 0;
  font-size: 1.3rem;
}

.error-message {
  background: rgb(var(--danger-rgb) / 0.16);
  color: var(--danger);
  padding: 0.8rem;
  border-radius: 6px;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 1.2rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.form-group label {
  color: var(--muted);
  font-size: 0.9rem;
  font-weight: 500;
}

.input,
.textarea {
  padding: 0.8rem;
  background: var(--glass-strong);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  font-size: 1rem;
  font-family: inherit;
  transition: border-color 0.2s;
}
.input:focus,
.textarea:focus {
  outline: none;
  border-color: var(--accent);
}
.input:disabled,
.textarea:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.textarea {
  resize: vertical;
  min-height: 100px;
}

.form-actions {
  display: flex;
  gap: 1rem;
  margin-top: 0.5rem;
}

.btn-submit {
  flex: 1;
  padding: 0.8rem;
}
.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.btn-cancel {
  padding: 0.8rem 1.5rem;
}
.btn-cancel:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.checking {
  color: var(--muted);
  padding: 0.8rem;
  text-align: center;
}

.cannot-create {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 0.9rem 1.1rem;
  border: 1px dashed rgb(var(--ink) / 0.28);
  border-radius: var(--radius-sm);
  color: var(--text);
}
.info-icon {
  flex: none;
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border: 1.5px solid var(--muted);
  border-radius: 50%;
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: 0.8rem;
  font-weight: 700;
}
.cannot-create p {
  margin: 0;
  font-size: 0.92rem;
  font-weight: 500;
}

@media (min-width: 640px) {
  .form-container {
    padding: 2rem;
  }
  
  .form-actions {
    flex-direction: row;
  }
  
  .btn-submit {
    flex: 1;
  }
}
</style>

