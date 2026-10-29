// Русские подписи статусов хакатонов и команд. В API и в CSS-классах остаются
// исходные значения (upcoming, open и т.д.), переводится только отображаемый текст.

const LABELS: Record<string, string> = {
  // хакатоны
  upcoming: 'Предстоящий',
  active: 'Активный',
  finished: 'Завершён',
  // команды
  open: 'Открыта',
  closed: 'Закрыта',
};

export function statusLabel(status: string | null | undefined): string {
  if (!status) return '';
  return LABELS[status] ?? status;
}

export const hackathonStatuses = [
  { value: 'upcoming', label: LABELS.upcoming },
  { value: 'active', label: LABELS.active },
  { value: 'finished', label: LABELS.finished },
];
