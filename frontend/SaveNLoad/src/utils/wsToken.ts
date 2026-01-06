const API_BASE = import.meta.env.VITE_API_BASE;

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
        const csrfToken = await ensureCsrf();
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
