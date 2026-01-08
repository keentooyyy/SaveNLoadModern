import { createApp, type Component } from 'vue';
import { createPinia, setActivePinia } from 'pinia';
import { notify } from '@/utils/notify';
import { useAuthStore } from '@/stores/auth';

const initToastr = () => {
  const t = (window as any).toastr;
  if (!t) {
    return;
  }
  t.options = {
    progressBar: true,
    closeButton: true,
    newestOnTop: true,
    positionClass: 'toast-top-right',
    timeOut: 4000
  };
};

const parseProps = (raw: string | null) => {
  if (!raw) {
    return {};
  }
  try {
    return JSON.parse(raw);
  } catch {
    return {};
  }
};

export const mountIsland = async (name: string, component: Component) => {
  const nodes = document.querySelectorAll<HTMLElement>(`[data-island="${name}"]`);
  if (!nodes.length) {
    return;
  }

  initToastr();
  notify.showFlash();

  for (const node of nodes) {
    const props = parseProps(node.getAttribute('data-props'));
    const app = createApp(component, props);
    const pinia = createPinia();
    app.use(pinia);
    setActivePinia(pinia);
    const auth = useAuthStore();
    await auth.initCsrf();
    app.mount(node);
  }
};
