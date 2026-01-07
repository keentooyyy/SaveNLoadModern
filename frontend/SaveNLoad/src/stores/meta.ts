import { defineStore } from 'pinia';
import { ref } from 'vue';

const API_BASE = import.meta.env.VITE_API_BASE;

export const useMetaStore = defineStore('meta', () => {
  const versionLabel = ref('v--');
  let versionPromise: Promise<void> | null = null;

  const normalizeVersion = (raw: string) => {
    if (!raw) {
      return 'v--';
    }
    return raw.startsWith('v') ? raw : `v${raw}`;
  };

  const loadVersion = async () => {
    if (versionPromise) {
      return versionPromise;
    }
    versionPromise = (async () => {
      try {
        const response = await fetch(`${API_BASE}/meta/version`, { credentials: 'include' });
        if (!response.ok) {
          return;
        }
        const data = await response.json();
        versionLabel.value = normalizeVersion(data?.version || '');
      } catch {
        // Keep fallback version label.
      }
    })();
    try {
      await versionPromise;
    } finally {
      versionPromise = null;
    }
  };

  const setVersion = (raw: string) => {
    versionLabel.value = normalizeVersion(raw);
  };

  return {
    versionLabel,
    loadVersion,
    setVersion
  };
});
