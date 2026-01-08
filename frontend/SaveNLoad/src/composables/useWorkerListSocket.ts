// WS mirror from SaveNLoad/templates/workerClaim.js.
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { buildWsUrl } from '@/utils/ws';
import { getSharedWsToken } from '@/utils/wsToken';
import { notify } from '@/utils/notify';
import type { Ref } from 'vue';

export type WorkerSnapshot = {
  client_id: string;
  claimed: boolean;
  linked_user?: string | null;
  hostname?: string | null;
  last_ping_response?: string | null;
};

type WorkersUpdateMessage = {
  type?: string;
  payload?: {
    workers?: WorkerSnapshot[];
  };
};

type WorkerListOptions = {
  reloadOnClose?: boolean;
  userRef: Ref<any | null>;
  getWsToken?: () => Promise<string | null>;
};

export const useWorkerListSocket = (options: WorkerListOptions) => {
  const workers = ref<WorkerSnapshot[]>([]);
  const socketOpen = ref(false);
  const lastError = ref('');
  const supportsWebSocket = ref(true);

  let socket: WebSocket | null = null;
  let reconnectTimer: number | null = null;
  let hasOpened = false;
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

  const handleMessage = (event: MessageEvent) => {
    try {
      const message: WorkersUpdateMessage = JSON.parse(event.data);
      if (message.type === 'workers_update') {
        workers.value = Array.isArray(message.payload?.workers) ? message.payload?.workers ?? [] : [];
      }
    } catch (error) {
      console.error('Workers WS message error:', error);
    }
  };

  const connect = async () => {
    if (!window.WebSocket) {
      supportsWebSocket.value = false;
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

    const wsUrl = buildWsUrl('/ws/ui/workers/', { token });
    socket = new WebSocket(wsUrl);

    socket.addEventListener('open', () => {
      socketOpen.value = true;
      hasOpened = true;
    });

    socket.addEventListener('message', handleMessage);

    socket.addEventListener('close', () => {
      socketOpen.value = false;
      if (options.reloadOnClose && hasOpened) {
        notify.flashWarning('Worker connection lost. Reloading...');
        window.location.reload();
        return;
      }
      if (shouldReconnect) {
        reconnectTimer = window.setTimeout(connect, 3000);
      }
    });

    socket.addEventListener('error', error => {
      lastError.value = 'Workers socket error';
      console.error('Workers WS error:', error);
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
    workers,
    socketOpen,
    lastError,
    supportsWebSocket
  };
};
