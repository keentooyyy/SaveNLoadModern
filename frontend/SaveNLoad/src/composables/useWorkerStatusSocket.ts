// WS mirror from SaveNLoad/templates/workerStatus.js.
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { buildWsUrl } from '@/utils/ws';
import { useDashboardStore } from '@/stores/dashboard';
import { useSettingsStore } from '@/stores/settings';
import { useAuthStore } from '@/stores/auth';

const API_BASE = import.meta.env.VITE_API_BASE;

type WorkerStatusMessage = {
  type?: string;
  payload?: {
    connected?: boolean;
  };
};

type WorkerStatusOptions = {
  onWorkerUnavailable?: () => void | Promise<void>;
};

export const useWorkerStatusSocket = (options: WorkerStatusOptions = {}) => {
  const workerAvailable = ref<boolean | null>(null);
  const socketOpen = ref(false);
  const lastError = ref('');
  const dashboardStore = useDashboardStore();
  const settingsStore = useSettingsStore();
  const authStore = useAuthStore();

  let socket: WebSocket | null = null;
  let reconnectTimer: number | null = null;
  let shouldReconnect = true;

  const getCookie = (name: string) => {
    const match = document.cookie.match(new RegExp(`(^|;\\s*)${name}=([^;]*)`));
    return match ? decodeURIComponent(match[2]) : '';
  };

  const ensureCsrf = async () => {
    const token = getCookie('csrftoken');
    if (token) {
      return token;
    }
    await fetch(`${API_BASE}/auth/csrf`, { credentials: 'include' });
    return getCookie('csrftoken');
  };

  const refreshSession = async () => {
    const csrfToken = await ensureCsrf();
    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken
      },
      credentials: 'include'
    });
    return response.ok;
  };

  const requestWithRetry = async (makeRequest: () => Promise<Response>) => {
    let response = await makeRequest();
    if (response.status === 401) {
      const refreshed = await refreshSession();
      if (refreshed) {
        response = await makeRequest();
      }
    }
    return response;
  };

  const fetchWsToken = async () => {
    if (dashboardStore.wsToken) {
      return dashboardStore.wsToken;
    }
    if (settingsStore.wsToken) {
      dashboardStore.wsToken = settingsStore.wsToken;
      return settingsStore.wsToken;
    }
    try {
      const csrfToken = await ensureCsrf();
      const response = await requestWithRetry(() => (
        fetch(`${API_BASE}/auth/ws-token/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrfToken
          },
          credentials: 'include'
        })
      ));
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        return null;
      }
      return data?.token || null;
    } catch {
      return null;
    }
  };

  const closeSocket = () => {
    shouldReconnect = false;
    if (reconnectTimer) {
      window.clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    if (socket) {
      socket.close();
      socket = null;
    }
  };

  const handleMessage = async (event: MessageEvent) => {
    try {
      const message: WorkerStatusMessage = JSON.parse(event.data);
      if (message.type === 'worker_status') {
        const connected = message.payload?.connected;
        workerAvailable.value = typeof connected === 'boolean' ? connected : null;
        if (connected === false && options.onWorkerUnavailable) {
          await options.onWorkerUnavailable();
        }
      }
    } catch (error) {
      console.error('Worker status WS message error:', error);
    }
  };

  const connect = async () => {
    if (!window.WebSocket) {
      return;
    }
    if (!authStore.user) {
      return;
    }

    const token = await fetchWsToken();
    if (!token) {
      return;
    }

    if (reconnectTimer) {
      window.clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }

    const wsUrl = buildWsUrl('/ws/ui/worker-status/', { token });
    socket = new WebSocket(wsUrl);

    socket.addEventListener('open', () => {
      socketOpen.value = true;
    });

    socket.addEventListener('message', handleMessage);

    socket.addEventListener('close', () => {
      socketOpen.value = false;
      if (shouldReconnect) {
        reconnectTimer = window.setTimeout(connect, 3000);
      }
    });

    socket.addEventListener('error', error => {
      lastError.value = 'Worker status socket error';
      console.error('Worker status WS error:', error);
      socket?.close();
    });
  };

  onMounted(connect);
  watch(
    () => authStore.user,
    () => {
      if (!socket && authStore.user) {
        connect();
      }
    }
  );
  onBeforeUnmount(closeSocket);

  return {
    workerAvailable,
    socketOpen,
    lastError
  };
};
