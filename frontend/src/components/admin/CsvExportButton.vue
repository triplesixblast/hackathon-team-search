<script setup lang="ts">
import { toast } from '../../composables/useFeedback';
import { ref, defineProps } from 'vue';
import { adminApiClient } from '../../utils/api';

const props = defineProps<{
  url: string;
  filename: string;
  label: string;
}>();

const downloading = ref(false);

async function downloadCsv() {
  downloading.value = true;
  try {
    const response = await adminApiClient.get(props.url, {
      responseType: 'blob',
    });
    const href = URL.createObjectURL(response.data);
    const link = document.createElement('a');
    link.href = href;
    link.setAttribute('download', props.filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(href);
  } catch (e: any) {
    toast.error('Ошибка экспорта CSV');
  } finally {
    downloading.value = false;
  }
}
</script>

<template>
  <button @click="downloadCsv" :disabled="downloading" class="csv-btn">
    <span v-if="!downloading">{{ props.label }}</span>
    <span v-else class="loader"></span>
  </button>
</template>

<style scoped lang="css">
.csv-btn {
  border: none;
  padding: 0.5rem 1.1rem;
  font-size: 1rem;
  border-radius: 6px;
  background: var(--accent);
  color: var(--on-accent);
  cursor: pointer;
  transition: background 0.15s;
  min-width: 120px;
  position: relative;
}
.csv-btn:disabled {
  background: var(--glass-strong);
  cursor: wait;
}

.loader {
  display: inline-block;
  width: 22px;
  height: 22px;
  border: 3px solid var(--text);
  border-radius: 50%;
  border-top-color: var(--accent);
  animation: spin-csv 0.7s linear infinite;
  vertical-align: middle;
}

@keyframes spin-csv {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>
