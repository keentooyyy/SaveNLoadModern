import { defineStore } from 'pinia';
import { ref } from 'vue';
import { apiDelete, apiGet, apiPost } from '@/utils/apiClient';

type DashboardUser = {
  id: number;
  username: string;
  role: string;
  email?: string;
};

type GameSummary = {
  id: number;
  title: string;
  image: string;
  footer: string;
  last_played_timestamp?: string | null;
  save_file_locations?: string[];
};

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

const resolveMediaUrl = (url: string) => {
  if (!url) {
    return url;
  }
  if (url.startsWith('/media/')) {
    return `${API_BASE}${url}`;
  }
  return url;
};

const normalizeGameImage = (game: GameSummary) => ({
  ...game,
  image: resolveMediaUrl(game.image || '')
});

export const useDashboardStore = defineStore('dashboard', () => {
  const user = ref<DashboardUser | null>(null);
  const isAdmin = ref(false);
  const recentGames = ref<GameSummary[]>([]);
  const games = ref<GameSummary[]>([]);
  const loading = ref(false);
  const operationLoading = ref(false);
  const error = ref('');
  const wsToken = ref('');
  const dashboardLoaded = ref(false);
  const bootstrapLoaded = dashboardLoaded;
  const lastLoadedAt = ref(0);
  let loadPromise: Promise<any> | null = null;
  const DASHBOARD_TTL_MS = 30000;

  const buildSnapshot = () => ({
    user: user.value,
    is_admin: isAdmin.value,
    recent_games: recentGames.value,
    available_games: games.value
  });

  const applyDashboardPayload = (data: any) => {
    user.value = data?.user || null;
    isAdmin.value = !!data?.is_admin;
    recentGames.value = (data?.recent_games || []).map(normalizeGameImage);
    games.value = (data?.available_games || []).map(normalizeGameImage);
    if (data?.ws_token) {
      wsToken.value = data.ws_token;
    }
  };

  const loadDashboard = async (options: { force?: boolean } = {}) => {
    const isFresh = dashboardLoaded.value && Date.now() - lastLoadedAt.value < DASHBOARD_TTL_MS;
    if (!options.force && isFresh && user.value) {
      return Promise.resolve(buildSnapshot());
    }
    if (loadPromise) {
      return loadPromise;
    }
    loading.value = true;
    error.value = '';
    loadPromise = (async () => {
      try {
        const data = await apiGet('/dashboard');
        applyDashboardPayload(data);
        dashboardLoaded.value = true;
        lastLoadedAt.value = Date.now();
        return data;
      } catch (err: any) {
        error.value = err?.message || '';
        throw err;
      } finally {
        loading.value = false;
        loadPromise = null;
      }
    })();
    return loadPromise;
  };

  const searchGames = async (query: string, sort: string) => {
    loading.value = true;
    error.value = '';
    try {
      const data = await apiGet('/games/search', { q: query, sort });
      games.value = (data?.games || []).map(normalizeGameImage);
      return data;
    } catch (err: any) {
      error.value = err?.message || '';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const saveGame = async (gameId: number) => {
    operationLoading.value = true;
    error.value = '';
    try {
      const data = await apiPost(`/games/${gameId}/save/`, {});
      return data;
    } catch (err: any) {
      error.value = err?.message || '';
      if (error.value) {
        notify.error(error.value);
      }
      throw err;
    } finally {
      operationLoading.value = false;
    }
  };

  const loadGame = async (gameId: number) => {
    operationLoading.value = true;
    error.value = '';
    try {
      const data = await apiPost(`/games/${gameId}/load/`, {});
      return data;
    } catch (err: any) {
      error.value = err?.message || '';
      if (error.value) {
        notify.error(error.value);
      }
      throw err;
    } finally {
      operationLoading.value = false;
    }
  };

  const loadGameSaveFolder = async (gameId: number, folderNumber: number) => {
    operationLoading.value = true;
    error.value = '';
    try {
      const data = await apiPost(`/games/${gameId}/load/`, { save_folder_number: folderNumber });
      return data;
    } catch (err: any) {
      error.value = err?.message || '';
      if (error.value) {
        notify.error(error.value);
      }
      throw err;
    } finally {
      operationLoading.value = false;
    }
  };

  const listSaveFolders = async (gameId: number) => {
    return apiGet(`/games/${gameId}/save-folders/`);
  };

  const deleteSaveFolder = async (gameId: number, folderNumber: number) => {
    return apiDelete(`/games/${gameId}/save-folders/${folderNumber}/delete/`);
  };

  const backupAllSaves = async (gameId: number) => {
    return apiPost(`/games/${gameId}/backup-all-saves/`, {});
  };

  const deleteAllSaves = async (gameId: number) => {
    return apiDelete(`/games/${gameId}/delete-all-saves/`);
  };

  const openSaveLocation = async (gameId: number) => {
    return apiPost(`/games/${gameId}/open-save-location/`, {});
  };

  const openBackupLocation = async (gameId: number, zipPath: string) => {
    return apiPost(`/games/${gameId}/open-backup-location/`, { zip_path: zipPath });
  };

  const deleteGame = async (gameId: number) => {
    operationLoading.value = true;
    error.value = '';
    try {
      const data = await apiDelete(`/games/${gameId}/delete/`);
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
      operationLoading.value = false;
    }
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

  const touchRecentGame = (gameId: number) => {
    const nowIso = new Date().toISOString();
    const footer = 'Last played just now';
    const source = games.value.find((game) => game.id === gameId)
      || recentGames.value.find((game) => game.id === gameId);
    if (!source) {
      return;
    }

    const updated = {
      ...source,
      footer,
      last_played_timestamp: nowIso
    };

    recentGames.value = [
      updated,
      ...recentGames.value.filter((game) => game.id !== gameId)
    ].slice(0, 10);

    games.value = games.value.map((game) => (
      game.id === gameId ? { ...game, footer, last_played_timestamp: nowIso } : game
    ));
  };

  return {
    user,
    isAdmin,
    recentGames,
    games,
    loading,
    operationLoading,
    error,
    wsToken,
    dashboardLoaded,
    bootstrapLoaded,
    lastLoadedAt,
    bootstrapDashboard: loadDashboard,
    loadDashboard,
    searchGames,
    saveGame,
    loadGame,
    loadGameSaveFolder,
    listSaveFolders,
    deleteSaveFolder,
    backupAllSaves,
    deleteAllSaves,
    openSaveLocation,
    openBackupLocation,
    checkOperationStatus,
    touchRecentGame,
    deleteGame
  };
});
