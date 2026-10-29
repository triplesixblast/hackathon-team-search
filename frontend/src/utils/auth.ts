/**
 * Утилиты для работы с авторизацией и cookie
 */
import { COOKIE_NAMES } from '../config';

export function getCookie(name: string): string | null {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()?.split(';').shift() || null;
  return null;
}

export function setCookie(name: string, value: string, days: number = 7): void {
  const maxAge = 60 * 60 * 24 * days;
  // SameSite=Lax не отправляет cookie с чужих сайтов; Secure добавляем на https
  const secure = window.location.protocol === 'https:' ? '; Secure' : '';
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${maxAge}; SameSite=Lax${secure}`;
}

export function deleteCookie(name: string): void {
  document.cookie = `${name}=; path=/; max-age=0`;
}

export function isUserAuthenticated(): boolean {
  return getCookie(COOKIE_NAMES.ACCESS_TOKEN) !== null;
}

export function isAdminAuthenticated(): boolean {
  return getCookie(COOKIE_NAMES.ADMIN_TOKEN) !== null;
}

export function logout(): void {
  deleteCookie(COOKIE_NAMES.ACCESS_TOKEN);
  deleteCookie(COOKIE_NAMES.USER_ID);
  window.location.href = '/auth';
}

export function adminLogout(): void {
  deleteCookie(COOKIE_NAMES.ADMIN_TOKEN);
  window.location.href = '/admin/login';
}

