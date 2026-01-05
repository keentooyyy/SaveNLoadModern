// WS mirror from SaveNLoad/templates/workerClaim.js.
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { buildWsUrl } from '@/utils/ws';

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
};

export const useWorkerListSocket = (options: WorkerListOptions = {}) => {
  const workers = ref<WorkerSnapshot[]>([]);
  const socketOpen = ref(false);
  const lastError = ref('');
  const supportsWebSocket = ref(true);

  let socket: WebSocket | null = null;
  let reconnectTimer: number | null = null;
  let hasOpened = false;

  const closeSocket = () => {
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

  const connect = () => {
    if (!window.WebSocket) {
      supportsWebSocket.value = false;
      return;
    }

    if (reconnectTimer) {
      window.clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }

    const wsUrl = buildWsUrl('/ws/ui/workers/');
    socket = new WebSocket(wsUrl);

    socket.addEventListener('open', () => {
      socketOpen.value = true;
      hasOpened = true;
    });

    socket.addEventListener('message', handleMessage);

    socket.addEventListener('close', () => {
      socketOpen.value = false;
      if (options.reloadOnClose && hasOpened) {
        window.location.reload();
        return;
      }
      reconnectTimer = window.setTimeout(connect, 3000);
    });

    socket.addEventListener('error', error => {
      lastError.value = 'Workers socket error';
      console.error('Workers WS error:', error);
      socket?.close();
    });
  };

  onMounted(connect);
  onBeforeUnmount(closeSocket);

  return {
    workers,
    socketOpen,
    lastError,
    supportsWebSocket
  };
};
