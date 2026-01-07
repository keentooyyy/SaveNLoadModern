import { createRouter, createWebHistory } from 'vue-router';
import LoginPage from '@/pages/LoginPage.vue';
import RegisterPage from '@/pages/RegisterPage.vue';
import ForgotPasswordPage from '@/pages/ForgotPasswordPage.vue';
import ResetPasswordPage from '@/pages/ResetPasswordPage.vue';
import VerifyOtpPage from '@/pages/VerifyOtpPage.vue';
import DashboardPage from '@/pages/DashboardPage.vue';
import GameDetailPage from '@/pages/GameDetailPage.vue';
import SettingsPage from '@/pages/SettingsPage.vue';
import WorkerRequiredPage from '@/pages/WorkerRequiredPage.vue';

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', component: LoginPage, alias: '/login', meta: { title: 'Login', authPage: true } },
    { path: '/register', component: RegisterPage, meta: { title: 'Register', authPage: true } },
    { path: '/forgot-password', component: ForgotPasswordPage, meta: { title: 'Forgot Password', authPage: true } },
    { path: '/reset-password', component: ResetPasswordPage, meta: { title: 'Reset Password', authPage: true } },
    { path: '/verify-otp', component: VerifyOtpPage, meta: { title: 'Verify OTP', authPage: true } },
    { path: '/dashboard', component: DashboardPage, meta: { title: 'Dashboard', requiresAuth: true } },
    { path: '/games/:id', component: GameDetailPage, meta: { title: 'Game Details', requiresAuth: true } },
    { path: '/settings', component: SettingsPage, meta: { title: 'Settings', requiresAuth: true } },
    { path: '/worker-required', component: WorkerRequiredPage, meta: { title: 'Connect Worker', requiresAuth: true } }
  ]
});

router.beforeEach((to) => {
  const currentPath = window.location.pathname + window.location.search + window.location.hash;
  if (currentPath !== to.fullPath) {
    window.location.assign(to.fullPath);
    return false;
  }
  return true;
});

export default router;
