// WS mirror from SaveNLoad/templates/workerStatus.js.
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { buildWsUrl } from '@/utils/ws';
import { getSharedWsToken } from '@/utils/wsToken';
import type { Ref } from 'vue';

type WorkerStatusMessage = {
  type?: string;
  payload?: {
    connected?: boolean;
  };
};

type WorkerStatusOptions = {
  onWorkerUnavailable?: () => void | Promise<void>;
  userRef: Ref<any | null>;
  suppressRedirectRef?: Ref<boolean>;
  getWsToken?: () => Promise<string | null>;
};

export const useWorkerStatusSocket = (options: WorkerStatusOptions) => {
  const workerAvailable = ref<boolean | null>(null);
  const socketOpen = ref(false);
  const lastError = ref('');

  let socket: WebSocket | null = null;
  let reconnectTimer: number | null = null;
  let shouldReconnect = true;

  const fetchWsToken = async () => {
    if (options.getWsToken) {
      return options.getWsToken();
    }
    return getSharedWsToken();
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
        const suppressRedirect = options.suppressRedirectRef?.value ?? false;
        if (connected === false && options.onWorkerUnavailable && !suppressRedirect) {
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
    if (!options.userRef?.value) {
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
    () => options.userRef?.value,
    () => {
      if (!socket && options.userRef?.value) {
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
