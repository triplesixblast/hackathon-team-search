<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { isUserAuthenticated } from '../utils/auth';
import apiClient from '../utils/api';

const route = useRoute();
const showNav = ref(isUserAuthenticated());
const pendingInvitationsCount = ref(0);
const loadingInvitations = ref(false);

const navItems = [
  { to: '/hackathons', label: 'Хакатоны', icon: ['M8 21h8', 'M12 17v4', 'M7 4h10v5a5 5 0 0 1-10 0V4z', 'M17 5h3v2a3 3 0 0 1-3 3', 'M7 5H4v2a3 3 0 0 0 3 3'] },
  { to: '/team', label: 'Команды', icon: ['M16 20v-1.5a3.5 3.5 0 0 0-3.5-3.5h-5A3.5 3.5 0 0 0 4 18.5V20', 'M10 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z', 'M20 20v-1.5a3.5 3.5 0 0 0-2.5-3.35', 'M15.5 4.2a3.5 3.5 0 0 1 0 6.6'] },
  { to: '/invitations', label: 'Уведомления', badge: true, icon: ['M18 16v-5a6 6 0 1 0-12 0v5l-2 2h16l-2-2z', 'M10 21a2 2 0 0 0 4 0'] },
  { to: '/profile', label: 'Профиль', icon: ['M20 21v-1.5a4.5 4.5 0 0 0-4.5-4.5h-7A4.5 4.5 0 0 0 4 19.5V21', 'M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z'] },
];
const activeIndex = computed(() =>
  navItems.findIndex((item) => route.path === item.to || route.path.startsWith(item.to + '/'))
);

// Обновляем состояние авторизации при изменении маршрута
watch(() => route.path, () => {
  showNav.value = isUserAuthenticated();
  if (showNav.value) {
    loadPendingInvitations();
  }
}, { immediate: true });

// Загружаем количество уведомлений (приглашения + заявки)
async function loadPendingInvitations() {
  if (!isUserAuthenticated()) {
    pendingInvitationsCount.value = 0;
    return;
  }
  
  loadingInvitations.value = true;
  try {
    // Загружаем просмотренные уведомления из localStorage
    let viewedNotifications: number[] = [];
    try {
      const viewed = localStorage.getItem('viewedNotifications');
      if (viewed) {
        viewedNotifications = JSON.parse(viewed);
      }
    } catch (e) {
      // Игнорируем ошибки
    }
    
    // Загружаем приглашения (фильтруем только pending для счетчика)
    const invitationsResponse = await apiClient.get('/api/invitations', {
      params: { status_filter: 'pending' }
    });
    // Считаем только непросмотренные pending приглашения
    let count = invitationsResponse.data?.filter((inv: any) => 
      inv.status === 'pending' && !viewedNotifications.includes(inv.id)
    )?.length || 0;
    
    // Загружаем заявки на вступление в мои команды (для капитана)
    try {
      const applicationsResponse = await apiClient.get('/api/invitations/applications');
      // Считаем только непросмотренные заявки
      const unviewedApplications = applicationsResponse.data?.filter((app: any) => 
        !viewedNotifications.includes(app.id)
      )?.length || 0;
      count += unviewedApplications;
    } catch {
      // Если нет заявок или пользователь не капитан, это нормально
    }
    
    pendingInvitationsCount.value = count;
  } catch {
    pendingInvitationsCount.value = 0;
  } finally {
    loadingInvitations.value = false;
  }
}

// Слушаем события обновления уведомлений
function handleNotificationsUpdated() {
  loadPendingInvitations();
}

// Слушаем события просмотра уведомлений
function handleNotificationsViewed() {
  loadPendingInvitations();
}

let pollTimer: ReturnType<typeof setInterval> | undefined;

onMounted(() => {
  showNav.value = isUserAuthenticated();
  if (showNav.value) {
    loadPendingInvitations();
    // Обновляем каждые 30 секунд
    pollTimer = setInterval(loadPendingInvitations, 30000);

    // Слушаем события обновления и просмотра уведомлений
    window.addEventListener('notifications-updated', handleNotificationsUpdated);
    window.addEventListener('notifications-viewed', handleNotificationsViewed);
  }
});

onUnmounted(() => {
  clearInterval(pollTimer);
  window.removeEventListener('notifications-updated', handleNotificationsUpdated);
  window.removeEventListener('notifications-viewed', handleNotificationsViewed);
});
</script>

<template>
  <div class="app-layout">
    <header class="main-header glass-panel">
      <div class="container">
        <router-link to="/" class="logo">ITAM HACK</router-link>
        <nav v-if="showNav" class="main-nav">
          <router-link to="/hackathons">Хакатоны</router-link>
          <router-link to="/team">Мои команды</router-link>
          <router-link to="/invitations" class="invitations-link">
            Уведомления
            <span v-if="pendingInvitationsCount > 0" class="invitations-badge">{{ pendingInvitationsCount }}</span>
          </router-link>
          <router-link to="/profile">Профиль</router-link>
        </nav>
      </div>
    </header>
    <main class="main-content">
      <router-view />
    </main>
    <!-- Мобильная навигация: liquid glass -->
    <svg class="lg-defs" width="0" height="0" aria-hidden="true" focusable="false">
      <filter id="liquid-refract" x="0%" y="0%" width="100%" height="100%" color-interpolation-filters="sRGB">
        <feTurbulence type="fractalNoise" baseFrequency="0.012 0.03" numOctaves="2" seed="7" result="noise" />
        <feGaussianBlur in="noise" stdDeviation="3" result="softNoise" />
        <feDisplacementMap in="SourceGraphic" in2="softNoise" scale="38" xChannelSelector="R" yChannelSelector="G" />
      </filter>
    </svg>
    <nav v-if="showNav" class="mobile-nav" :style="{ '--i': activeIndex, '--n': navItems.length }">
      <div class="lg-refract" aria-hidden="true"></div>
      <div class="lg-tint" aria-hidden="true"></div>
      <div class="lg-lens" :class="{ 'no-active': activeIndex < 0 }" aria-hidden="true"></div>
      <router-link v-for="item in navItems" :key="item.to" :to="item.to" class="lg-item">
        <svg class="lg-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path v-for="d in item.icon" :key="d" :d="d" />
        </svg>
        <span class="lg-label">{{ item.label }}</span>
        <span v-if="item.badge && pendingInvitationsCount > 0" class="invitations-badge-mobile">{{ pendingInvitationsCount }}</span>
      </router-link>
    </nav>
  </div>
</template>

<style scoped lang="css">
.app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: transparent;
  color: var(--text);
}

.main-header {
  background: rgb(var(--shade) / 0.0);
  background: color-mix(in srgb, var(--bg-main) 82%, transparent);
  border: 0;
  border-bottom: 1px solid var(--border);
  box-shadow: none;
  padding: 0.55rem 0;
  backdrop-filter: blur(var(--blur-strong)) saturate(1.4);
  -webkit-backdrop-filter: blur(var(--blur-strong)) saturate(1.4);
  position: sticky;
  top: 0;
  z-index: 20;
  border-radius: 0;
  overflow: visible;
}

.logo {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.05rem;
  letter-spacing: -0.02em;
  margin-right: 2rem;
  color: var(--text);
  text-decoration: none;
}

.main-header .container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.logo {
  font-size: 1.15rem;
  margin-right: 1rem;
}
.main-nav {
  display: none;
  gap: 1.5rem;
}
.main-nav a {
  color: var(--muted);
  font-weight: 550;
  text-decoration: none;
  font-size: 1rem;
  position: relative;
  padding: 0.5rem 0.25rem;
  transition: color 0.2s ease;
}
.main-nav a.router-link-active {
  color: var(--accent);
}
.main-nav a::after {
  content: '';
  display: block;
  width: 0; height: 2px;
  background: var(--accent);
  transition: width .3s;
  position: absolute;
  left: 0; bottom: -3px;
}
.main-nav a:hover::after,
.main-nav a.router-link-active::after {
  width: 100%;
}

.invitations-link {
  position: relative;
}

.invitations-badge {
  position: absolute;
  top: -8px;
  right: -12px;
  background: var(--danger);
  color: #fff;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: bold;
  line-height: 1;
  box-shadow: 0 0 0 4px rgb(var(--danger-rgb) / 0.15);
}

.invitations-badge-mobile {
  position: absolute;
  top: 4px;
  left: calc(50% + 6px);
  background: var(--danger);
  color: #fff;
  border-radius: 50%;
  min-width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.65rem;
  font-weight: bold;
  padding: 0 4px;
  line-height: 1;
  box-shadow: 0 0 0 4px rgb(var(--danger-rgb) / 0.18);
}

.main-content {
  flex: 1;
  max-width: 1100px;
  width: 100%;
  margin: 0 auto;
  padding: 1.5rem 1rem 5rem 1rem;
}
.main-footer {
  text-align: center;
  font-size: 0.95rem;
  background: #222237;
  padding: 0.8rem;
  color: #aaa;
  font-weight: 400;
}
.lg-defs {
  position: absolute;
  pointer-events: none;
}

/* Liquid glass: плавающая капсула с преломлением фона */
.mobile-nav {
  --pad: 6px;
  --radius: 30px;
  display: grid;
  grid-template-columns: repeat(var(--n, 4), 1fr);
  position: fixed;
  left: 50%;
  bottom: calc(14px + env(safe-area-inset-bottom, 0px));
  width: min(calc(100vw - 28px), 460px);
  transform: translateX(-50%);
  padding: var(--pad);
  border-radius: var(--radius);
  z-index: 31;
  isolation: isolate;
  box-shadow:
    0 18px 44px rgb(var(--shade) / 0.28),
    0 2px 6px rgb(var(--shade) / 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.55),
    inset 0 -1px 0 rgba(255, 255, 255, 0.12),
    inset 1px 0 0 rgba(255, 255, 255, 0.2),
    inset -1px 0 0 rgba(255, 255, 255, 0.2);
}
/* преломляющий слой: размытие + искажение + насыщенность фона */
.lg-refract {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  z-index: -3;
  -webkit-backdrop-filter: blur(14px) saturate(1.8) brightness(1.08);
  backdrop-filter: blur(14px) saturate(1.8) brightness(1.08);
}
@supports (backdrop-filter: url(#x)) and (not (-webkit-hyphens: none)) {
  .lg-refract {
    backdrop-filter: blur(6px) url(#liquid-refract) saturate(1.8) brightness(1.08);
  }
}
/* тонировка и блик */
.lg-tint {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  z-index: -2;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.28) 0%, rgba(255, 255, 255, 0.04) 38%, rgba(255, 255, 255, 0.0) 60%, rgba(255, 255, 255, 0.1) 100%),
    var(--nav-base);
  pointer-events: none;
}
/* «линза» активного пункта: скользит между вкладками с пружинкой */
.lg-lens {
  position: absolute;
  top: var(--pad);
  bottom: var(--pad);
  left: var(--pad);
  width: calc((100% - var(--pad) * 2) / var(--n));
  transform: translateX(calc(var(--i, 0) * 100%));
  border-radius: calc(var(--radius) - var(--pad));
  z-index: -1;
  background: var(--lens-bg);
  -webkit-backdrop-filter: blur(4px) saturate(2) brightness(1.25);
  backdrop-filter: blur(4px) saturate(2) brightness(1.25);
  box-shadow:
    inset 0 1px 1px rgba(255, 255, 255, 0.8),
    inset 0 -2px 8px rgb(var(--accent-rgb) / 0.3),
    inset 0 0 14px rgba(255, 255, 255, 0.18),
    0 6px 18px rgb(var(--shade) / 0.22),
    0 0 24px rgb(var(--accent-rgb) / 0.22);
  transition:
    transform 0.55s cubic-bezier(0.34, 1.56, 0.64, 1),
    opacity 0.25s ease;
  pointer-events: none;
}
.lg-lens.no-active {
  opacity: 0;
}
.lg-item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  padding: 0.55rem 0.1rem 0.5rem;
  color: var(--nav-ink);
  text-decoration: none;
  border-radius: calc(var(--radius) - var(--pad));
  transition: color 0.25s ease, transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
  -webkit-user-select: none;
  user-select: none;
}
.lg-item:active {
  transform: scale(0.92);
}
.lg-item.router-link-active {
  color: var(--nav-ink-active);
}
.lg-icon {
  width: 24px;
  height: 24px;
  filter: drop-shadow(0 2px 5px rgb(var(--shade) / 0.25));
  transition: transform 0.45s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.lg-item.router-link-active .lg-icon {
  transform: translateY(-1px) scale(1.12);
  stroke: currentColor;
}
.lg-label {
  font-size: 0.66rem;
  font-weight: 650;
  letter-spacing: 0.01em;
  line-height: 1.1;
  white-space: nowrap;
}
@media (prefers-reduced-motion: reduce) {
  .lg-lens, .lg-item, .lg-icon { transition: none; }
}
/* без поддержки backdrop-filter — плотная подложка */
@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) {
  .mobile-nav { background: var(--glass-strong); }
}
@media (min-width: 768px) {
  .main-header .container {
    padding: 0 1.4rem;
  }
  .logo {
    font-size: 1.3rem;
    margin-right: 2rem;
  }
  .main-nav {
    display: flex;
  }
  .mobile-nav {
    display: none;
  }
  .main-content {
    padding: 2rem 1.1rem 2rem 1.1rem;
  }
}
@media (min-width: 1024px) {
  .main-content {
    padding: 2rem 1.5rem;
  }
}
</style>
