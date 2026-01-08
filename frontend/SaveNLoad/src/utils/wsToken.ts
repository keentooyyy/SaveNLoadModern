import { ensureCsrfToken, requestWithRetry } from '@/utils/apiClient';

const API_BASE = import.meta.env.VITE_API_BASE;

let wsTokenPromise: Promise<string | null> | null = null;
let cachedToken: string | null = null;

export const getSharedWsToken = async () => {
  if (cachedToken) {
    return cachedToken;
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
          cachedToken = token;
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
