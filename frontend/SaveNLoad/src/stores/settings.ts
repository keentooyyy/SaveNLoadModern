import { defineStore } from 'pinia';
import { ref } from 'vue';
import { apiDelete, apiGet, apiPost } from '@/utils/apiClient';

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

export const useSettingsStore = defineStore('settings', () => {
  const loading = ref(false);
  const error = ref('');
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
  const usersLoaded = ref(false);
  const statsLoaded = ref(false);
  const lastUsersLoadedAt = ref(0);
  const lastStatsLoadedAt = ref(0);
  const lastUsersQuery = ref('');
  const lastUsersPage = ref(1);
  let usersPromise: Promise<any> | null = null;
  let statsPromise: Promise<any> | null = null;
  const USERS_TTL_MS = 30000;
  const STATS_TTL_MS = 15000;
  const wsToken = ref('');
  const bootstrapLoaded = ref(false);
  const bootstrapData = ref<{ user?: any | null; version?: string } | null>(null);
  let bootstrapPromise: Promise<any> | null = null;
  const resetState = () => {
    loading.value = false;
    error.value = '';
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
    usersLoaded.value = false;
    statsLoaded.value = false;
    lastUsersLoadedAt.value = 0;
    lastStatsLoadedAt.value = 0;
    lastUsersQuery.value = '';
    lastUsersPage.value = 1;
    wsToken.value = '';
    bootstrapLoaded.value = false;
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

  const listUsers = async (query = '', page = 1, options: { force?: boolean } = {}) => {
    const sameRequest = lastUsersQuery.value === query && lastUsersPage.value === page;
    const isFresh = usersLoaded.value && Date.now() - lastUsersLoadedAt.value < USERS_TTL_MS;
    if (!options.force && sameRequest && isFresh) {
      return Promise.resolve({
        users: users.value,
        pagination: usersPagination.value
      });
    }
    if (usersPromise && sameRequest) {
      return usersPromise;
    }
    lastUsersQuery.value = query;
    lastUsersPage.value = page;
    usersPromise = (async () => {
      const data = await apiGet('/users/', { q: query, page: String(page) });
      users.value = data?.users || [];
      usersPagination.value = data?.pagination || usersPagination.value;
      usersLoaded.value = true;
      lastUsersLoadedAt.value = Date.now();
      return data;
    })();
    return usersPromise.finally(() => {
      usersPromise = null;
    });
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

  const queueStats = async (options: { force?: boolean } = {}) => {
    const isFresh = statsLoaded.value && Date.now() - lastStatsLoadedAt.value < STATS_TTL_MS;
    if (!options.force && isFresh) {
      return Promise.resolve(queueStatsData.value);
    }
    if (statsPromise) {
      return statsPromise;
    }
    statsPromise = (async () => {
      const data = await apiGet('/operations/queue/stats/');
      queueStatsData.value = data?.data || data || queueStatsData.value;
      statsLoaded.value = true;
      lastStatsLoadedAt.value = Date.now();
      return data;
    })();
    return statsPromise.finally(() => {
      statsPromise = null;
    });
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
        const [userPayload, versionPayload] = await Promise.all([
          apiGet('/auth/me'),
          apiGet('/meta/version').catch(() => null)
        ]);
        bootstrapLoaded.value = true;
        bootstrapData.value = {
          user: userPayload?.user || null,
          version: versionPayload?.version
        };
        return bootstrapData.value;
      } catch (err: any) {
        error.value = err?.message || '';
        throw err;
      } finally {
        loading.value = false;
        bootstrapPromise = null;
      }
    })();
    return bootstrapPromise;
  };

  return {
    loading,
    error,
    users,
    usersPagination,
    queueStatsData,
    wsToken,
    resetState,
    usersLoaded,
    statsLoaded,
    lastUsersLoadedAt,
    lastStatsLoadedAt,
    bootstrapLoaded,
    createGame,
    updateGame,
    listUsers,
    resetUserPassword,
    deleteUser,
    checkOperationStatus,
    queueStats,
    cleanupQueue,
    updateAccount,
    bootstrapSettings
  };
});
