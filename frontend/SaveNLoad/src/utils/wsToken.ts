import { ensureCsrfToken, requestWithRetry } from '@/utils/apiClient';

const API_BASE = import.meta.env.VITE_API_BASE;

let wsTokenPromise: Promise<string | null> | null = null;

export const getSharedWsToken = async (dashboardStore: any, settingsStore: any) => {
  if (dashboardStore.wsToken) {
    return dashboardStore.wsToken;
  }
  if (settingsStore.wsToken) {
    dashboardStore.wsToken = settingsStore.wsToken;
    return settingsStore.wsToken;
  }

  if (!wsTokenPromise) {
    wsTokenPromise = (async () => {
      try {
        const csrfToken = await ensureCsrfToken();
        const response = await requestWithRetry(() => (
          fetch(`${API_BASE}/auth/ws-token/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken },
            credentials: 'include'
          })
        ));
        const data = await response.json().catch(() => null);
        if (!response.ok) {
          return null;
        }
        const token = data?.token || null;
        if (token) {
          dashboardStore.wsToken = token;
        }
        return token;
      } catch {
        return null;
      } finally {
        wsTokenPromise = null;
      }
    })();
  }

  return wsTokenPromise;
};
