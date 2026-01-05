import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';
import './styles/custom.css';
import './styles/app.css';
import { useAuthStore } from './stores/auth';

const app = createApp(App);

const initToastr = () => {
  const t = (window as any).toastr;
  if (!t) {
    console.error('Toastr not loaded. Check /vendor/toastr/toastr.min.js and index.html order.');
    return;
  }
  t.options = {
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
  await auth.initCsrf();
});

router.afterEach((to) => {
  const title = typeof to.meta?.title === 'string' ? to.meta.title : 'Save N Load';
  document.title = `${title}`;
});

app.mount('#app');
