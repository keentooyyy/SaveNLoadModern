import { createRouter, createWebHistory } from 'vue-router';
import LoginPage from '@/pages/LoginPage.vue';
import RegisterPage from '@/pages/RegisterPage.vue';
import ForgotPasswordPage from '@/pages/ForgotPasswordPage.vue';
import ResetPasswordPage from '@/pages/ResetPasswordPage.vue';
import VerifyOtpPage from '@/pages/VerifyOtpPage.vue';
import DashboardPage from '@/pages/DashboardPage.vue';
import SettingsPage from '@/pages/SettingsPage.vue';
import WorkerRequiredPage from '@/pages/WorkerRequiredPage.vue';
import { useAuthStore } from '@/stores/auth';
import { useDashboardStore } from '@/stores/dashboard';
import { useMetaStore } from '@/stores/meta';
import { useSettingsStore } from '@/stores/settings';

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', component: LoginPage, alias: '/login', meta: { title: 'Login', authPage: true } },
    { path: '/register', component: RegisterPage, meta: { title: 'Register', authPage: true } },
    { path: '/forgot-password', component: ForgotPasswordPage, meta: { title: 'Forgot Password', authPage: true } },
    { path: '/reset-password', component: ResetPasswordPage, meta: { title: 'Reset Password', authPage: true } },
    { path: '/verify-otp', component: VerifyOtpPage, meta: { title: 'Verify OTP', authPage: true } },
    { path: '/dashboard', component: DashboardPage, meta: { title: 'Dashboard', requiresAuth: true } },
    { path: '/settings', component: SettingsPage, meta: { title: 'Settings', requiresAuth: true } },
    { path: '/worker-required', component: WorkerRequiredPage, meta: { title: 'Connect Worker', requiresAuth: true } }
  ]
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();
    if (to.path === '/dashboard') {
    const dashboard = useDashboardStore();
    const meta = useMetaStore();

    const clientId = window.localStorage.getItem('savenload_client_id');
    if (!clientId) {
      return true; // skip bootstrap when no worker is linked
    }

    try {
      const data = await dashboard.bootstrapDashboard();
      if (data?.user) {
        auth.user = data.user as any;
      }
      if (data?.version) {
        meta.setVersion(data.version);
      }
    } catch (err: any) {
      const status = err?.status;
      if (status === 401) {
        return { path: '/' };
      }
      if (status === 503) {
        return { path: '/worker-required' };
      }
    }
  }
  else if (to.path === '/settings') {
    const settingsStore = useSettingsStore();
    const meta = useMetaStore();
    try {
      const data = await settingsStore.bootstrapSettings();
      if (data?.user) {
        auth.user = data.user as any;
      }
      if (data?.version) {
        meta.setVersion(data.version);
      }
    } catch (err: any) {
      const status = err?.status;
      if (status === 401) {
        return { path: '/' };
      }
    }
  } else {
    await auth.bootstrap();
  }
  const isAuthed = !!auth.user;

  if (to.meta?.requiresAuth && !isAuthed) {
    return { path: '/' };
  }

  if (to.meta?.authPage && isAuthed) {
    return { path: '/dashboard' };
  }

  return true;
});

export default router;
