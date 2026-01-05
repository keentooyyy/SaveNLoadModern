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

export const useDashboardStore = defineStore('dashboard', () => {
  const user = ref<DashboardUser | null>(null);
  const isAdmin = ref(false);
  const recentGames = ref<GameSummary[]>([]);
  const games = ref<GameSummary[]>([]);
  const loading = ref(false);
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

  return {
    user,
    isAdmin,
    recentGames,
    games,
    loading,
    error,
    loadDashboard,
    searchGames
  };
});
