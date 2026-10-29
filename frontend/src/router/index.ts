import { createRouter, createWebHistory } from 'vue-router';
import AppLayout from '../layouts/AppLayout.vue';
import AdminLayout from '../layouts/AdminLayout.vue';
import { isUserAuthenticated, isAdminAuthenticated } from '../utils/auth';

// Auth components
import TelegramLogin from '../components/auth/TelegramLogin.vue';
import AdminLogin from '../components/auth/AdminLogin.vue';

// Profile components
import ProfileView from '../components/profile/ProfileView.vue';
import ProfileEdit from '../components/profile/ProfileEdit.vue';

// Hackathons components
import HackathonsList from '../components/hackathons/HackathonsList.vue';
import HackathonsDetail from '../components/hackathons/HackathonsDetail.vue';

// Teams components
import MyTeam from '../components/teams/MyTeam.vue';
import TeamDetail from '../components/teams/TeamDetail.vue';

// Invitations components
import InvitationsList from '../components/invitations/InvitationsList.vue';

// Admin components
import AdminDashboard from '../components/admin/AdminDashboard.vue';
import HackathonAdminList from '../components/admin/HackathonAdminList.vue';

// Home page
import Home from '../components/Home.vue';
import Dashboard from '../components/Dashboard.vue';

const routes = [
  {
    path: '/',
    component: AppLayout,
    children: [
      {
        path: '',
        name: 'home',
        component: Home,
        meta: { requiresAuth: false }
      },
      {
        path: 'dashboard',
        name: 'dashboard',
        component: Dashboard,
        meta: { requiresAuth: true }
      },
      {
        path: 'auth',
        name: 'auth',
        component: TelegramLogin,
        meta: { requiresAuth: false }
      },
      {
        path: 'profile',
        name: 'profile',
        component: ProfileView,
        meta: { requiresAuth: true }
      },
      {
        path: 'profile/edit',
        name: 'profile-edit',
        component: ProfileEdit,
        meta: { requiresAuth: true }
      },
      {
        path: 'hackathons',
        name: 'hackathons',
        component: HackathonsList,
        meta: { requiresAuth: true }
      },
      {
        path: 'hackathons/:id',
        name: 'hackathon-detail',
        component: HackathonsDetail,
        props: true,
        meta: { requiresAuth: true }
      },
      {
        path: 'team',
        name: 'team',
        component: MyTeam,
        meta: { requiresAuth: true }
      },
      {
        path: 'teams/:id',
        name: 'team-detail',
        component: TeamDetail,
        props: true,
        meta: { requiresAuth: true }
      },
      {
        path: 'invitations',
        name: 'invitations',
        component: InvitationsList,
        meta: { requiresAuth: true }
      }
    ]
  },
  {
    path: '/admin',
    component: AdminLayout,
    children: [
      {
        path: 'login',
        name: 'admin-login',
        component: AdminLogin,
        meta: { requiresAdminAuth: false }
      },
      {
        path: '',
        name: 'admin-dashboard',
        component: AdminDashboard,
        meta: { requiresAdminAuth: true }
      },
      {
        path: 'hackathons',
        name: 'admin-hackathons',
        component: HackathonAdminList,
        meta: { requiresAdminAuth: true }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

// Navigation guards
router.beforeEach((to, _from, next) => {
  // Check for admin routes
  if (to.matched.some(record => record.path.startsWith('/admin'))) {
    if (to.meta.requiresAdminAuth && !isAdminAuthenticated()) {
      next({ name: 'admin-login' });
      return;
    }
    if (to.name === 'admin-login' && isAdminAuthenticated()) {
      next({ name: 'admin-dashboard' });
      return;
    }
    next();
    return;
  }

  // Check for user routes
  if (to.meta.requiresAuth && !isUserAuthenticated()) {
    next({ name: 'auth' });
    return;
  }

  // Redirect from auth page if already authenticated
  if (to.name === 'auth' && isUserAuthenticated()) {
    next({ name: 'dashboard' });
    return;
  }

  // Redirect authenticated users from home to dashboard (только если авторизован)
  if (to.name === 'home' && (isUserAuthenticated() || isAdminAuthenticated())) {
    if (isAdminAuthenticated()) {
      next({ name: 'admin-dashboard' });
    } else {
      next({ name: 'dashboard' });
    }
    return;
  }

  next();
});

export default router;

