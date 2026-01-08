import { defineStore } from 'pinia';
import { ref } from 'vue';
import { apiDelete, apiGet, apiPatch, apiPost } from '@/utils/apiClient';
import { notify } from '@/utils/notify';

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
  const wsToken = ref('');
  const adminSettings = ref<Record<string, any>>({});
  const adminSettingsSaving = ref(false);
  const adminSettingsHealthLoading = ref(false);
  const adminSettingsRevealLoading = ref(false);
  const adminSettingsHealth = ref<Record<string, any> | null>(null);
  const workers = ref<any[]>([]);
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
    wsToken.value = '';
    adminSettings.value = {};
    adminSettingsSaving.value = false;
    adminSettingsHealthLoading.value = false;
    adminSettingsRevealLoading.value = false;
    adminSettingsHealth.value = null;
    workers.value = [];
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

  const loadAdminSettings = async () => {
    adminSettingsSaving.value = true;
    try {
      const data = await apiGet('/admin/settings');
      adminSettings.value = data?.settings || {};
      return adminSettings.value;
    } catch (err: any) {
      error.value = err?.message || '';
      throw err;
    } finally {
      adminSettingsSaving.value = false;
    }
  };

  const updateAdminSettings = async (payload: Record<string, any>) => {
    adminSettingsSaving.value = true;
    try {
      const data = await apiPatch('/admin/settings', { settings: payload });
      adminSettings.value = { ...adminSettings.value, ...(data?.settings || {}) };
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
      adminSettingsSaving.value = false;
    }
  };

  const checkAdminSettingsHealth = async () => {
    adminSettingsHealthLoading.value = true;
    try {
      const data = await apiPost('/admin/settings/health', {});
      adminSettingsHealth.value = data?.health || null;
      return adminSettingsHealth.value;
    } catch (err: any) {
      error.value = err?.message || '';
      if (error.value) {
        notify.error(error.value);
      }
      throw err;
    } finally {
      adminSettingsHealthLoading.value = false;
    }
  };

  const revealAdminSettings = async (keys: string[], password: string) => {
    adminSettingsRevealLoading.value = true;
    try {
      const data = await apiPost('/admin/settings/reveal', { keys, password });
      adminSettings.value = { ...adminSettings.value, ...(data?.settings || {}) };
      return data?.settings || {};
    } catch (err: any) {
      error.value = err?.message || '';
      if (error.value) {
        notify.error(error.value);
      }
      throw err;
    } finally {
      adminSettingsRevealLoading.value = false;
    }
  };

  const listWorkers = async () => {
    const data = await apiGet('/client/workers/');
    workers.value = data?.workers || [];
    return data;
  };

  const unclaimAllWorkers = async () => {
    const data = await apiPost('/client/unclaim-all/', {});
    if (data?.message) {
      notify.success(data.message);
    }
    workers.value = data?.workers || workers.value;
    return data;
  };

  return {
    loading,
    error,
    users,
    usersPagination,
    queueStatsData,
    wsToken,
    adminSettings,
    adminSettingsSaving,
    adminSettingsHealthLoading,
    adminSettingsRevealLoading,
    adminSettingsHealth,
    workers,
    resetState,
    createGame,
    updateGame,
    listUsers,
    resetUserPassword,
    deleteUser,
    checkOperationStatus,
    queueStats,
    cleanupQueue,
    updateAccount,
    loadAdminSettings,
    updateAdminSettings,
    checkAdminSettingsHealth,
    revealAdminSettings,
    listWorkers,
    unclaimAllWorkers
  };
});
