const API_BASE = import.meta.env.VITE_API_BASE || '';

export const getCookie = (name: string) => {
  const match = document.cookie.match(new RegExp(`(^|;\\s*)${name}=([^;]*)`));
  return match?.[2] ? decodeURIComponent(match[2]) : '';
};

export const ensureCsrfToken = async () => {
  const token = getCookie('csrftoken');
  if (token) {
    return token;
  }
  await fetch(`${API_BASE}/auth/csrf`, { credentials: 'include' });
  return getCookie('csrftoken');
};

export const refreshSession = async () => {
  const csrfToken = await ensureCsrfToken();
  const response = await fetch(`${API_BASE}/auth/refresh`, {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrfToken
    },
    credentials: 'include'
  });
  return response.ok;
};

export const requestWithRetry = async (makeRequest: () => Promise<Response>) => {
  let response = await makeRequest();
  if (response.status === 401) {
    const refreshed = await refreshSession();
    if (refreshed) {
      response = await makeRequest();
    }
  }
  return response;
};

export const safeJsonParse = async (response: Response) => {
  try {
    return await response.json();
  } catch {
    return null;
  }
};

export const buildApiUrl = (path: string, params?: Record<string, string>) => {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== '') {
        url.searchParams.set(key, value);
      }
    });
  }
  return url.toString();
};

const assertResponseOk = (response: Response, data: any) => {
  if (!response.ok) {
    const error = new Error(data?.error || data?.message || '');
    (error as any).status = response.status;
    (error as any).data = data;
    throw error;
  }
};

export const apiGet = async (path: string, params?: Record<string, string>) => {
  const response = await requestWithRetry(() => (
    fetch(buildApiUrl(path, params), { credentials: 'include' })
  ));
  const data = await safeJsonParse(response);
  assertResponseOk(response, data);
  return data;
};

export const apiPost = async (path: string, body: Record<string, unknown>) => {
  const csrfToken = await ensureCsrfToken();
  const response = await requestWithRetry(() => (
    fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      credentials: 'include',
      body: JSON.stringify(body)
    })
  ));
  const data = await safeJsonParse(response);
  assertResponseOk(response, data);
  return data;
};

export const apiDelete = async (path: string) => {
  const csrfToken = await ensureCsrfToken();
  const response = await requestWithRetry(() => (
    fetch(`${API_BASE}${path}`, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': csrfToken
      },
      credentials: 'include'
    })
  ));
  const data = await safeJsonParse(response);
  assertResponseOk(response, data);
  return data;
};

export const apiPatch = async (path: string, body: Record<string, unknown>) => {
  const csrfToken = await ensureCsrfToken();
  const response = await requestWithRetry(() => (
    fetch(`${API_BASE}${path}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      credentials: 'include',
      body: JSON.stringify(body)
    })
  ));
  const data = await safeJsonParse(response);
  assertResponseOk(response, data);
  return data;
};
