<script setup lang="ts">
import { feedback, dismissToast } from '../composables/useFeedback';
</script>

<template>
  <div class="toast-stack" aria-live="polite">
    <TransitionGroup name="toast">
      <div
        v-for="t in feedback.toasts"
        :key="t.id"
        class="toast"
        :class="t.type"
        role="status"
        @click="dismissToast(t.id)"
      >
        <span class="toast-dot" aria-hidden="true"></span>
        <span>{{ t.message }}</span>
      </div>
    </TransitionGroup>
  </div>

  <Transition name="fade">
    <div
      v-if="feedback.confirm"
      class="confirm-backdrop"
      @click.self="feedback.confirm.resolve(false)"
      @keydown.esc="feedback.confirm.resolve(false)"
    >
      <div class="confirm-card" role="alertdialog" aria-modal="true">
        <p>{{ feedback.confirm.message }}</p>
        <div class="confirm-actions">
          <button type="button" class="btn-ghost" @click="feedback.confirm.resolve(false)">Отмена</button>
          <button
            type="button"
            class="confirm-ok"
            :class="{ danger: feedback.confirm.danger }"
            autofocus
            @click="feedback.confirm.resolve(true)"
          >
            {{ feedback.confirm.confirmText }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped lang="css">
.toast-stack {
  position: fixed;
  top: calc(14px + env(safe-area-inset-top, 0px));
  left: 50%;
  transform: translateX(-50%);
  width: min(calc(100vw - 28px), 420px);
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 100;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.8rem 1.1rem;
  border-radius: 16px;
  background: var(--float-bg);
  border: 1px solid var(--border);
  color: var(--text);
  font-size: 0.95rem;
  font-weight: 550;
  box-shadow: var(--shadow-strong), inset 0 1px 0 var(--glass-hl);
  backdrop-filter: blur(var(--blur-strong)) saturate(1.6);
  -webkit-backdrop-filter: blur(var(--blur-strong)) saturate(1.6);
  pointer-events: auto;
  cursor: pointer;
}

.toast-dot {
  flex: none;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--accent);
}
.toast.success .toast-dot { background: var(--accent-3); }
.toast.error .toast-dot { background: var(--danger); }

.toast-enter-active,
.toast-leave-active {
  transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.25s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-16px) scale(0.96);
}

.confirm-backdrop {
  position: fixed;
  inset: 0;
  z-index: 110;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background: rgb(var(--shade) / 0.35);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}

.confirm-card {
  width: min(100%, 380px);
  padding: 1.4rem;
  border-radius: 28px;
  background: var(--float-bg);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-strong), inset 0 1px 0 var(--glass-hl);
  backdrop-filter: blur(var(--blur-strong)) saturate(1.6);
  -webkit-backdrop-filter: blur(var(--blur-strong)) saturate(1.6);
  color: var(--text);
}

.confirm-card p {
  font-size: 1.05rem;
  font-weight: 550;
  line-height: 1.4;
  margin-bottom: 1.2rem;
}

.confirm-actions {
  display: flex;
  gap: 0.6rem;
  justify-content: flex-end;
}

.confirm-ok.danger {
  background: var(--danger);
  color: #fff;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
