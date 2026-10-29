<script setup lang="ts">
import { statusLabel } from '../../utils/statusLabels';
import { computed, defineProps } from 'vue';

const props = defineProps<{
  team: any;
}>();

function plural(n: number, forms: [string, string, string]): string {
  const m10 = n % 10;
  const m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return forms[0];
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return forms[1];
  return forms[2];
}

const memberCountLabel = computed(() => {
  const n = props.team.members?.length || 0;
  return `${n} ${plural(n, ['участник', 'участника', 'участников'])}`;
});
</script>

<template>
  <div class="team-card">
    <h3>{{ props.team.name }}</h3>
    <p v-if="props.team.description" class="description">{{ props.team.description }}</p>
    <div class="meta">
      <span class="status" :class="props.team.status">{{ statusLabel(props.team.status) }}</span>
      <span class="members-count">{{ memberCountLabel }}</span>
    </div>
    <div v-if="props.team.members && props.team.max_team_size" class="capacity-info">
      <span class="capacity-text">{{ props.team.members.length }} / {{ props.team.max_team_size }}</span>
      <span v-if="props.team.members.length >= props.team.max_team_size" class="full-badge">Полная</span>
    </div>
    <router-link :to="`/teams/${props.team.id}`" class="btn-view">Подробнее</router-link>
  </div>
</template>

<style scoped lang="css">
.team-card {
  background: var(--glass);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-soft);
  backdrop-filter: blur(var(--blur-soft)) saturate(1.4);
  -webkit-backdrop-filter: blur(var(--blur-soft)) saturate(1.4);
  border-radius: 12px;
  padding: 1.5rem;
  color: var(--text);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.team-card h3 {
  margin: 0;
  color: var(--accent);
}

.description {
  color: var(--muted);
  font-size: 0.9rem;
  flex: 1;
}

.meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
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

.btn-view {
  text-align: center;
}

.capacity-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
  color: var(--muted);
  margin-top: 0.5rem;
}

.capacity-text {
  font-weight: 600;
}

.full-badge {
  background: rgb(var(--danger-rgb) / 0.16);
  color: var(--danger);
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}
</style>

