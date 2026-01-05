import { createRouter, createWebHistory } from 'vue-router';
import LoginPage from '@/pages/LoginPage.vue';
import RegisterPage from '@/pages/RegisterPage.vue';
import ForgotPasswordPage from '@/pages/ForgotPasswordPage.vue';
import ResetPasswordPage from '@/pages/ResetPasswordPage.vue';
import VerifyOtpPage from '@/pages/VerifyOtpPage.vue';
import DashboardPage from '@/pages/DashboardPage.vue';
import SettingsPage from '@/pages/SettingsPage.vue';
import WorkerRequiredPage from '@/pages/WorkerRequiredPage.vue';

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/login' },
    { path: '/login', component: LoginPage, meta: { title: 'Login' } },
    { path: '/register', component: RegisterPage, meta: { title: 'Register' } },
    { path: '/forgot-password', component: ForgotPasswordPage, meta: { title: 'Forgot Password' } },
    { path: '/reset-password', component: ResetPasswordPage, meta: { title: 'Reset Password' } },
    { path: '/verify-otp', component: VerifyOtpPage, meta: { title: 'Verify OTP' } },
    { path: '/dashboard', component: DashboardPage, meta: { title: 'Dashboard' } },
    { path: '/settings', component: SettingsPage, meta: { title: 'Settings' } },
    { path: '/worker-required', component: WorkerRequiredPage, meta: { title: 'Connect Worker' } }
  ]
});

export default router;
