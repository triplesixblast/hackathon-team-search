/**
 * Конфигурация приложения
 */

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_BACKEND_URL ||
  import.meta.env.BACKEND_URL ||
  '';

export const APP_NAME = 'ITAM Hack Platform';

export const ROUTES = {
  HOME: '/',
  DASHBOARD: '/dashboard',
  AUTH: '/auth',
  PROFILE: '/profile',
  PROFILE_EDIT: '/profile/edit',
  HACKATHONS: '/hackathons',
  HACKATHON_DETAIL: (id: number) => `/hackathons/${id}`,
  TEAM: '/team',
  TEAM_DETAIL: (id: number) => `/teams/${id}`,
  INVITATIONS: '/invitations',
  ADMIN_LOGIN: '/admin/login',
  ADMIN_DASHBOARD: '/admin',
  ADMIN_HACKATHONS: '/admin/hackathons',
} as const;

export const COOKIE_NAMES = {
  ACCESS_TOKEN: 'access_token',
  USER_ID: 'user_id',
  ADMIN_TOKEN: 'admin_token',
} as const;

export const HACKATHON_STATUSES = {
  UPCOMING: 'upcoming',
  ACTIVE: 'active',
  FINISHED: 'finished',
} as const;

export const TEAM_STATUSES = {
  OPEN: 'open',
  CLOSED: 'closed',
} as const;

export const INVITATION_STATUSES = {
  PENDING: 'pending',
  ACCEPTED: 'accepted',
  DECLINED: 'declined',
} as const;

export const EXPERIENCE_LEVELS = {
  JUNIOR: 'junior',
  MIDDLE: 'middle',
  SENIOR: 'senior',
} as const;

export const ROLE_PREFERENCES = {
  FRONTEND: 'frontend',
  BACKEND: 'backend',
  FULLSTACK: 'fullstack',
  DESIGNER: 'designer',
} as const;

