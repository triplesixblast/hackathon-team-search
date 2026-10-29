import { reactive } from 'vue';

export type ToastType = 'success' | 'error' | 'info';

export interface Toast {
  id: number;
  type: ToastType;
  message: string;
}

interface ConfirmState {
  message: string;
  confirmText: string;
  danger: boolean;
  resolve: (ok: boolean) => void;
}

const TOAST_TTL = 3500;
let nextId = 1;

// Состояние общее для всего приложения: один FeedbackHost в App.vue
export const feedback = reactive<{ toasts: Toast[]; confirm: ConfirmState | null }>({
  toasts: [],
  confirm: null,
});

export function dismissToast(id: number) {
  feedback.toasts = feedback.toasts.filter((t) => t.id !== id);
}

function push(type: ToastType, message: string) {
  const id = nextId++;
  feedback.toasts.push({ id, type, message });
  setTimeout(() => dismissToast(id), type === 'error' ? TOAST_TTL * 1.5 : TOAST_TTL);
}

export const toast = {
  success: (message: string) => push('success', message),
  error: (message: string) => push('error', message),
  info: (message: string) => push('info', message),
};

/** Замена window.confirm: возвращает true, если пользователь подтвердил */
export function confirmDialog(
  message: string,
  options: { confirmText?: string; danger?: boolean } = {},
): Promise<boolean> {
  // Новый запрос закрывает предыдущий как отклонённый
  feedback.confirm?.resolve(false);
  return new Promise((resolve) => {
    feedback.confirm = {
      message,
      confirmText: options.confirmText ?? 'Подтвердить',
      danger: options.danger ?? false,
      resolve: (ok) => {
        feedback.confirm = null;
        resolve(ok);
      },
    };
  });
}
