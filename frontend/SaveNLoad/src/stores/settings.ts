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

async function apiGet(path: string, params?: Record<string, string>) {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== '') {
        url.searchParams.set(key, value);
      }
    });
  }

  const response = await requestWithRetry(() => (
    fetch(url.toString(), { credentials: 'include' })
  ));

  let data: any = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const error = new Error(data?.error || data?.message || '');
    (error as any).status = response.status;
    (error as any).data = data;
    throw error;
  }

  return data;
}

async function apiPost(path: string, body: Record<string, unknown>) {
  const csrfToken = await ensureCsrf();
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

  let data: any = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const error = new Error(data?.error || data?.message || '');
    (error as any).status = response.status;
    (error as any).data = data;
    throw error;
  }

  return data;
}

async function apiDelete(path: string) {
  const csrfToken = await ensureCsrf();
  const response = await requestWithRetry(() => (
    fetch(`${API_BASE}${path}`, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': csrfToken
      },
      credentials: 'include'
    })
  ));

  let data: any = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const error = new Error(data?.error || data?.message || '');
    (error as any).status = response.status;
    (error as any).data = data;
    throw error;
  }

  return data;
}

export const useSettingsStore = defineStore('settings', () => {
  const loading = ref(false);
  const error = ref('');
  const currentUser = ref<any | null>(null);
  const isAdmin = ref(false);
  const users = ref<any[]>([]);
  const usersPagination = ref({
    page: 1,
    page_size: 25,
    total_count: 0,
    total_pages: 1,
    has_next: false,
    has_previous: false
  });
  const queueStatsData = ref({
    total: 0,
    by_status: {
      pending: 0,
      in_progress: 0,
      completed: 0,
      failed: 0
    }
  });
  const bootstrapLoaded = ref(false);
  const bootstrapUsersLoaded = ref(false);
  const bootstrapStatsLoaded = ref(false);
  const wsToken = ref('');
  const bootstrapData = ref<any | null>(null);
  let bootstrapPromise: Promise<any> | null = null;
  const resetState = () => {
    loading.value = false;
    error.value = '';
    currentUser.value = null;
    isAdmin.value = false;
    users.value = [];
    usersPagination.value = {
      page: 1,
      page_size: 25,
      total_count: 0,
      total_pages: 1,
      has_next: false,
      has_previous: false
    };
    queueStatsData.value = {
      total: 0,
      by_status: {
        pending: 0,
        in_progress: 0,
        completed: 0,
        failed: 0
      }
    };
    bootstrapLoaded.value = false;
    bootstrapUsersLoaded.value = false;
    bootstrapStatsLoaded.value = false;
    wsToken.value = '';
    bootstrapData.value = null;
    bootstrapPromise = null;
  };

  const createGame = async (payload: { name: string; save_file_locations: string[]; banner?: string }) => {
    loading.value = true;
    error.value = '';
    try {
      const data = await apiPost('/games/create/', payload);
      if (data?.message) {
        notify.success(data.message);
      }
      return data;
    } catch (err: any) {
      error.value = err?.message || '';
      if (error.value) {
        notify.error(error.value);
      }
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const updateGame = async (gameId: number, payload: { name: string; save_file_locations: string[]; banner?: string }) => {
    loading.value = true;
    error.value = '';
    try {
      const data = await apiPost(`/games/${gameId}/update/`, payload);
      if (data?.message) {
        notify.success(data.message);
      }
      return data;
    } catch (err: any) {
      error.value = err?.message || '';
      if (error.value) {
        notify.error(error.value);
      }
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const listUsers = async (query = '', page = 1) => {
    const data = await apiGet('/users/', { q: query, page: String(page) });
    users.value = data?.users || [];
    usersPagination.value = data?.pagination || usersPagination.value;
    bootstrapUsersLoaded.value = true;
    return data;
  };

  const resetUserPassword = async (userId: number) => {
    const data = await apiPost(`/users/${userId}/reset-password/`, {});
    if (data?.message) {
      notify.success(data.message);
    }
    return data;
  };

  const deleteUser = async (userId: number) => {
    const data = await apiDelete(`/users/${userId}/delete/`);
    return data;
  };

  const checkOperationStatus = async (operationId: string) => {
    const data = await apiGet(`/operations/${operationId}/status/`);
    if (!data?.success && data?.error) {
      const error = new Error(data.error);
      (error as any).status = 400;
      throw error;
    }
    return data;
  };

  const queueStats = async () => {
    const data = await apiGet('/operations/queue/stats/');
    queueStatsData.value = data?.data || data || queueStatsData.value;
    bootstrapStatsLoaded.value = true;
    return data;
  };

  const cleanupQueue = async (type: string) => {
    const data = await apiPost('/operations/queue/cleanup/', { type });
    if (data?.message) {
      notify.success(data.message);
    }
    return data;
  };

  const updateAccount = async (payload: {
    email?: string;
    current_password?: string;
    new_password?: string;
    confirm_password?: string;
  }) => {
    const data = await apiPost('/account/update/', payload);
    if (data?.message) {
      notify.success(data.message);
    }
    return data;
  };

  const bootstrapSettings = async () => {
    if (bootstrapPromise) {
      return bootstrapPromise;
    }
    if (bootstrapLoaded.value && bootstrapData.value) {
      return Promise.resolve(bootstrapData.value);
    }
    loading.value = true;
    error.value = '';
    bootstrapPromise = (async () => {
      try {
        const data = await apiGet('/settings/bootstrap');
        bootstrapData.value = data;
        currentUser.value = data?.user || null;
        isAdmin.value = !!data?.is_admin;
        if (Array.isArray(data?.users)) {
          users.value = data.users;
          usersPagination.value = data?.pagination || usersPagination.value;
          bootstrapUsersLoaded.value = true;
        }
        if (data?.queue_stats) {
          queueStatsData.value = data.queue_stats;
          bootstrapStatsLoaded.value = true;
        }
        if (data?.ws_token) {
          wsToken.value = data.ws_token;
        }
        bootstrapLoaded.value = true;
        return data;
      } catch (err: any) {
        error.value = err?.message || '';
        bootstrapPromise = null;
        throw err;
      } finally {
        loading.value = false;
      }
    })();
    return bootstrapPromise;
  };

  const loadCurrentUser = async () => {
    if (currentUser.value) {
      return currentUser.value;
    }
    const data = await bootstrapSettings();
    return data?.user || null;
  };

  return {
    loading,
    error,
    currentUser,
    isAdmin,
    users,
    usersPagination,
    queueStatsData,
    wsToken,
    resetState,
    bootstrapLoaded,
    bootstrapUsersLoaded,
    bootstrapStatsLoaded,
    createGame,
    updateGame,
    listUsers,
    resetUserPassword,
    deleteUser,
    checkOperationStatus,
    queueStats,
    cleanupQueue,
    updateAccount,
    bootstrapSettings,
    loadCurrentUser
  };
});
