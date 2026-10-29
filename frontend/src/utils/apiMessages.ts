// Перевод сообщений API на русский. Бэкенд отдаёт англоязычные тексты ошибок,
// а логика бэкенда и тестов на них завязана, поэтому переводим на стороне фронтенда.

const EXACT: Record<string, string> = {
  'Invalid email or password': 'Неверный email или пароль',
  'Forbidden': 'Доступ запрещён',
  'Invalid or expired token': 'Сессия истекла, войдите заново',
  'Invalid token or insufficient permissions': 'Недостаточно прав, войдите заново',
  'Admin access required': 'Нужны права администратора',
  'Admin not found': 'Администратор не найден',

  'User not found': 'Пользователь не найден',
  'Team not found': 'Команда не найдена',
  'Hackathon not found': 'Хакатон не найден',
  'Invitation not found': 'Приглашение не найдено',
  'Member not found in team': 'Участник не найден в команде',
  'Team not found in this hackathon': 'Команда не найдена в этом хакатоне',

  'Hackathon is finished': 'Хакатон уже завершён',
  'Already registered for this hackathon': 'Вы уже зарегистрированы на этот хакатон',
  'Hackathon with this name already exists': 'Хакатон с таким названием уже существует',
  'end_date must be later than start_date': 'Дата окончания должна быть позже даты начала',

  'You must register for the hackathon first': 'Сначала зарегистрируйтесь на хакатон',
  'User must register for the hackathon first': 'Пользователь должен сначала зарегистрироваться на хакатон',
  'The applicant must register for the hackathon first': 'Заявитель должен сначала зарегистрироваться на хакатон',
  'User is not registered for this hackathon': 'Пользователь не зарегистрирован на этот хакатон',

  'You are already in a team for this hackathon': 'Вы уже состоите в команде на этом хакатоне',
  'You are already in another team for this hackathon': 'Вы уже состоите в другой команде на этом хакатоне',
  'User is already in a team for this hackathon': 'Пользователь уже состоит в команде на этом хакатоне',
  'You have already created a team for this hackathon': 'Вы уже создали команду на этом хакатоне',
  'You are already a member of this team': 'Вы уже состоите в этой команде',
  'User is already a member of this team': 'Пользователь уже состоит в этой команде',
  'You are already the captain': 'Вы уже капитан',
  'You are the captain of this team': 'Вы капитан этой команды',
  'You are not a member of this team': 'Вы не состоите в этой команде',
  'Team is not accepting new members': 'Команда не принимает новых участников',
  'New captain must be a member of the team': 'Новый капитан должен быть участником команды',
  'Team captain cannot be removed. Transfer captaincy first or delete the team.':
    'Капитана нельзя исключить. Сначала передайте роль капитана или удалите команду',
  'Team captain cannot be unassigned. Transfer captaincy first.':
    'Капитана нельзя убрать из команды. Сначала передайте роль капитана',
  "You don't have permission to remove this member": 'У вас нет прав исключать этого участника',
  'Only team captain can do this': 'Это может сделать только капитан команды',
  'Only team captain can send invitations': 'Приглашать может только капитан команды',
  'Only team captain can view invitations': 'Приглашения видит только капитан команды',
  'Only team captain can answer applications': 'На заявки отвечает только капитан команды',

  'This invitation is not for you': 'Это приглашение адресовано не вам',
  "This is an application, not an invitation. Please wait for the captain's response.":
    'Это ваша заявка, а не приглашение. Дождитесь ответа капитана',
  'This is an invitation, not an application': 'Это приглашение, а не заявка',
  'You cannot cancel this invitation': 'Вы не можете отменить это приглашение',
};

const PATTERNS: Array<[RegExp, (m: RegExpMatchArray) => string]> = [
  [/^Team is full\. Maximum team size is (\d+)$/, (m) => `Команда заполнена. Максимальный размер команды: ${m[1]}`],
  [/^Some team already has (\d+) members$/, (m) => `В одной из команд уже ${m[1]} участников`],
];

/** Русский текст для известного сообщения API; неизвестные возвращаются как есть */
export function translateApi<T>(message: T): T | string {
  if (typeof message !== 'string') return message;
  const exact = EXACT[message];
  if (exact) return exact;
  for (const [re, fn] of PATTERNS) {
    const m = message.match(re);
    if (m) return fn(m);
  }
  return message;
}

const VALIDATION_PATTERNS: Array<[RegExp, (m: RegExpMatchArray) => string]> = [
  [/^Field required$/, () => 'обязательное поле'],
  [/^String should have at most (\d+) characters?$/, (m) => `не длиннее ${m[1]} символов`],
  [/^String should have at least (\d+) characters?$/, (m) => `не короче ${m[1]} символов`],
  [/^Input should be a valid (.+)$/, () => 'некорректное значение'],
  [/^Value error, (.+)$/, (m) => m[1] ?? ''],
];

function validationText(item: any): string {
  const msg = typeof item?.msg === 'string' ? item.msg : 'некорректное значение';
  let text = msg;
  for (const [re, fn] of VALIDATION_PATTERNS) {
    const m = msg.match(re);
    if (m) {
      text = fn(m);
      break;
    }
  }
  // Последний элемент loc это имя поля (первый "body")
  const loc = Array.isArray(item?.loc) ? item.loc.filter((x: unknown) => x !== 'body') : [];
  const field = loc.length ? String(loc[loc.length - 1]) : '';
  return field ? `${field}: ${text}` : text;
}

/**
 * Приводит error.response.data.detail к строке на русском на месте, чтобы все экраны
 * получили готовый текст. FastAPI на ошибках валидации (422) отдаёт массив объектов.
 */
export function localizeError(error: any): void {
  const data = error?.response?.data;
  if (!data) return;
  if (typeof data.detail === 'string') {
    data.detail = translateApi(data.detail);
  } else if (Array.isArray(data.detail)) {
    data.detail = data.detail.map(validationText).join('; ');
  }
}
