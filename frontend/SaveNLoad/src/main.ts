import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';
import './styles/custom.css';
import './styles/app.css';
import { useAuthStore } from './stores/auth';

const app = createApp(App);

app.use(createPinia());
app.use(router);

router.isReady().then(async () => {
  const auth = useAuthStore();
  await auth.initCsrf();
});

router.afterEach((to) => {
  const title = typeof to.meta?.title === 'string' ? to.meta.title : 'Save N Load';
  document.title = `${title}`;
});

app.mount('#app');
