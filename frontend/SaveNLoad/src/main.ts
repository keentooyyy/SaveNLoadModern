import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';
import './styles/custom.css';
import './styles/app.css';
import { useAuthStore } from './stores/auth';
import { useDashboardStore } from './stores/dashboard';
import { useMetaStore } from './stores/meta';
import { useSettingsStore } from './stores/settings';

const app = createApp(App);

const initToastr = () => {
  const t = (window as any).toastr;
  t.options = {
    progressBar: true,
    closeButton: true,
    newestOnTop: true,
    positionClass: 'toast-top-right',
    timeOut: 4000
  };
};

app.use(createPinia());
app.use(router);

initToastr();

router.isReady().then(async () => {
  const auth = useAuthStore();
  const dashboard = useDashboardStore();
  const meta = useMetaStore();
  const settingsStore = useSettingsStore();
  await auth.initCsrf();
  if (router.currentRoute.value.path === '/dashboard') {
    if (!dashboard.bootstrapLoaded) {
      const data = await dashboard.bootstrapDashboard();
      if (data?.user) {
        auth.user = data.user as any;
      }
      if (data?.version) {
        meta.setVersion(data.version);
      }
    }
  } else if (router.currentRoute.value.path === '/settings') {
    if (!settingsStore.bootstrapLoaded) {
      const data = await settingsStore.bootstrapSettings();
      if (data?.user) {
        auth.user = data.user as any;
      }
      if (data?.version) {
        meta.setVersion(data.version);
      }
    }
  } else {
    await auth.bootstrap();
  }
});

router.afterEach((to) => {
  const title = typeof to.meta?.title === 'string' ? to.meta.title : 'Save N Load';
  document.title = `${title}`;
});

app.mount('#app');
