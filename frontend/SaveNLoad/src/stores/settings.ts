import { defineStore } from 'pinia';
import { ref } from 'vue';

const API_BASE = import.meta.env.VITE_API_BASE;

const notify = {
  success: (msg: string) => {
    const t = (window as any).toastr;
    if (t?.success) {
      t.success(msg);
    }
  },
  error: (msg: string) => {
    const t = (window as any).toastr;
    if (t?.error) {
      t.error(msg);
    }
  }
};

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

async function apiGet(path: string, params?: Record<string, string>) {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== '') {
        url.searchParams.set(key, value);
      }
    });
  }

  const response = await fetch(url.toString(), { credentials: 'include' });

  let data: any = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const error = new Error(data?.error || data?.message || 'Request failed');
    (error as any).status = response.status;
    (error as any).data = data;
    throw error;
  }

  return data;
}

async function apiPost(path: string, body: Record<string, unknown>) {
  const csrfToken = await ensureCsrf();
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken
    },
    credentials: 'include',
    body: JSON.stringify(body)
  });

  let data: any = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const error = new Error(data?.error || data?.message || 'Request failed');
    (error as any).status = response.status;
    (error as any).data = data;
    throw error;
  }

  return data;
}

async function apiDelete(path: string) {
  const csrfToken = await ensureCsrf();
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'DELETE',
    headers: {
      'X-CSRFToken': csrfToken
    },
    credentials: 'include'
  });

  let data: any = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const error = new Error(data?.error || data?.message || 'Request failed');
    (error as any).status = response.status;
    (error as any).data = data;
    throw error;
  }

  return data;
}

export const useSettingsStore = defineStore('settings', () => {
  const loading = ref(false);
  const error = ref('');

  const createGame = async (payload: { name: string; save_file_locations: string[]; banner?: string }) => {
    loading.value = true;
    error.value = '';
    try {
      const data = await apiPost('/games/create/', payload);
      notify.success(data?.message || 'Game created.');
      return data;
    } catch (err: any) {
      error.value = err?.message || 'Failed to create game.';
      notify.error(error.value);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const listUsers = async (query = '', page = 1) => {
    return apiGet('/users/', { q: query, page: String(page) });
  };

  const resetUserPassword = async (userId: number) => {
    const data = await apiPost(`/users/${userId}/reset-password/`, {});
    notify.success(data?.message || 'Password reset.');
    return data;
  };

  const deleteUser = async (userId: number) => {
    const data = await apiDelete(`/users/${userId}/delete/`);
    notify.success(data?.message || 'User deleted.');
    return data;
  };

  const queueStats = async () => {
    return apiGet('/operations/queue/stats/');
  };

  const cleanupQueue = async (type: string) => {
    const data = await apiPost('/operations/queue/cleanup/', { type });
    notify.success(data?.message || 'Operations cleared.');
    return data;
  };

  const updateAccount = async (payload: {
    email?: string;
    current_password?: string;
    new_password?: string;
    confirm_password?: string;
  }) => {
    const data = await apiPost('/account/update/', payload);
    notify.success(data?.message || 'Account updated.');
    return data;
  };

  const loadCurrentUser = async () => {
    const data = await apiGet('/dashboard');
    return data?.user || null;
  };

  return {
    loading,
    error,
    createGame,
    listUsers,
    resetUserPassword,
    deleteUser,
    queueStats,
    cleanupQueue,
    updateAccount,
    loadCurrentUser
  };
});
