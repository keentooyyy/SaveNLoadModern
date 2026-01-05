import { defineStore } from 'pinia';
import { ref } from 'vue';

type DashboardUser = {
  id: number;
  username: string;
  role: string;
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
    const error = new Error(data?.error || 'Request failed');
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

export const useDashboardStore = defineStore('dashboard', () => {
  const user = ref<DashboardUser | null>(null);
  const isAdmin = ref(false);
  const recentGames = ref<GameSummary[]>([]);
  const games = ref<GameSummary[]>([]);
  const loading = ref(false);
  const operationLoading = ref(false);
  const error = ref('');

  const loadDashboard = async () => {
    loading.value = true;
    error.value = '';
    try {
      const data = await apiGet('/dashboard');
      user.value = data?.user || null;
      isAdmin.value = !!data?.is_admin;
      recentGames.value = (data?.recent_games || []).map(normalizeGameImage);
      games.value = (data?.available_games || []).map(normalizeGameImage);
      return data;
    } catch (err: any) {
      error.value = err?.message || 'Failed to load dashboard.';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const searchGames = async (query: string, sort: string) => {
    loading.value = true;
    error.value = '';
    try {
      const data = await apiGet('/games/search', { q: query, sort });
      games.value = (data?.games || []).map(normalizeGameImage);
      return data;
    } catch (err: any) {
      error.value = err?.message || 'Failed to load games.';
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
      const message = data?.message || 'Save queued.';
      if (!message.toLowerCase().includes('operations queued')) {
        notify.success(message);
      }
      return data;
    } catch (err: any) {
      error.value = err?.message || 'Failed to save game.';
      notify.error(error.value);
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
      const message = data?.message || 'Load queued.';
      if (!message.toLowerCase().includes('operations queued')) {
        notify.success(message);
      }
      return data;
    } catch (err: any) {
      error.value = err?.message || 'Failed to load game.';
      notify.error(error.value);
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

  return {
    user,
    isAdmin,
    recentGames,
    games,
    loading,
    operationLoading,
    error,
    loadDashboard,
    searchGames,
    saveGame,
    loadGame,
    checkOperationStatus
  };
});
