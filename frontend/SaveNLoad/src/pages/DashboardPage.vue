<template>
  <AppLayout :version-label="versionLabel" :on-logout="onLogout" :on-load-version="loadVersion">
    <div class="container-fluid px-0">
      <PageHeader
        title="Home"
        :user-label="headerName"
        :user-role="headerRole"
        @profile="goToProfile"
        @settings="goToSettings"
        @logout="onLogout"
      />
      <div v-if="showGuestBanner" class="guest-expiry-banner mx-3 mt-3">
        <div class="guest-expiry-banner__icon">
          <i class="fas fa-user-clock"></i>
        </div>
        <div class="guest-expiry-banner__content">
          <div class="guest-expiry-banner__title">Guest account expires soon</div>
          <div class="guest-expiry-banner__meta">
            Deletion on {{ guestExpiryDate }} · {{ guestDaysLeft }} left
          </div>
        </div>
        <button class="guest-expiry-banner__cta" type="button" @click="goToSettings">
          Upgrade Account
        </button>
      </div>
      <RecentList :items="recentGames" :loading="recentLoading" @select="onRecentSelect" />
      <GameGrid
        v-model:search="searchQuery"
        v-model:sort="sortBy"
        :games="games"
        :loading="gamesLoading"
        :saving-id="savingGameId"
        :loading-id="loadingGameId"
        :searching="searching"
        @search="onSearch"
        @open="onOpenGame"
        @save="onSaveGame"
        @load="onQuickLoadGame"
      />
    </div>
  </AppLayout>
  <GameSavesModal
    :open="savesModalOpen"
    :title="selectedGameTitle"
    :save-folders="saveFolders"
    :loading="saveFoldersLoading"
    :error="saveFoldersError"
    :is-admin="isAdmin"
    @close="closeSavesModal"
    @load="onLoadSaveFolder"
    @delete="onDeleteSaveFolder"
    @backup-all="onBackupAllSaves"
    @delete-all="onDeleteAllSaves"
    @open-location="onOpenSaveLocation"
    @edit-game="onEditGame"
    @delete-game="onDeleteGame"
  />
  <OperationProgressModal
    :open="operationModal.open"
    :title="operationModal.title"
    :subtitle="operationModal.subtitle"
    :status-text="operationModal.statusText"
    :detail="operationModal.detail"
    :progress="operationModal.progress"
    :variant="operationModal.variant"
    :closable="operationModal.closable"
    @close="closeOperationModal"
  />
  <BackupCompleteModal
    :open="backupModal.open"
    :zip-path="backupModal.zipPath"
    @close="closeBackupModal"
    @open-location="onOpenBackupLocation"
  />
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, toRef } from 'vue';
import PageHeader from '@/components/organisms/PageHeader.vue';
import RecentList from '@/components/organisms/RecentList.vue';
import GameGrid from '@/components/organisms/GameGrid.vue';
import GameSavesModal from '@/components/organisms/GameSavesModal.vue';
import OperationProgressModal from '@/components/organisms/OperationProgressModal.vue';
import BackupCompleteModal from '@/components/organisms/BackupCompleteModal.vue';
import AppLayout from '@/layouts/AppLayout.vue';
import { useDashboardStore } from '@/stores/dashboard';
import { useAuthStore } from '@/stores/auth';
import { useMetaStore } from '@/stores/meta';
import { notify } from '@/utils/notify';
import { pauseBootstrapModals, restoreBootstrapModals } from '@/utils/modalStack';
import { useConfirm } from '@/composables/useConfirm';
import { useWorkerStatusSocket } from '@/composables/useWorkerStatusSocket';
import { getSharedWsToken } from '@/utils/wsToken';
import { redirectToWorkerRequired } from '@/utils/workerRequiredRedirect';

const store = useDashboardStore();
const authStore = useAuthStore();
const metaStore = useMetaStore();
const { requestConfirm } = useConfirm();
const suppressRedirectRef = toRef(authStore, 'suppressWorkerRedirect');

const searchQuery = ref('');
const sortBy = ref('name_asc');

const games = computed(() => store.games);
const recentGames = computed(() => store.recentGames);
const recentLoading = computed(() => store.loading && recentGames.value.length === 0);
const gamesLoading = computed(() => store.loading && games.value.length === 0);
const isAdmin = computed(() => store.isAdmin);
const dashboardError = computed(() => store.error);
const headerName = computed(() => store.user?.username || authStore.user?.username || '');
const headerRole = computed(() => (store.user?.role || authStore.user?.role || '').toUpperCase());
const versionLabel = computed(() => metaStore.versionLabel);
const guestExpiresAt = computed(() => {
  const value = store.user?.guest_expires_at || authStore.user?.guest_expires_at;
  return value ? new Date(value) : null;
});
const showGuestBanner = computed(() => {
  const isGuest = store.user?.is_guest ?? authStore.user?.is_guest;
  return !!isGuest && guestExpiresAt.value;
});
const isMigrating = computed(() => authStore.user?.guest_migration_status === 'migrating');
const now = ref(Date.now());
let bannerTimer: number | null = null;
const selectedGameTitle = ref('');
const selectedGameId = ref<number | null>(null);
const savesModalOpen = ref(false);
const saveFolders = ref<any[]>([]);
const saveFoldersLoading = ref(false);
const saveFoldersError = ref('');
const savingGameId = ref<number | null>(null);
const loadingGameId = ref<number | null>(null);
const searching = ref(false);
let searchRequestId = 0;

const operationModal = reactive({
  open: false,
  title: 'Operation in progress',
  subtitle: 'This can take a minute. Keep this window open.',
  statusText: 'Preparing...',
  detail: 'We are syncing your data.',
  progress: 0,
  variant: 'info',
  closable: false,
  pauseToken: null as string | null
});

const backupModal = reactive({
  open: false,
  zipPath: '',
  gameId: null as number | null,
  pending: false,
  pauseToken: null as string | null
});
const restoreGameSavesModal = ref(false);

let successCloseTimer: number | null = null;
let backupCloseTimer: number | null = null;

const guestExpiryDate = computed(() => {
  if (!guestExpiresAt.value) {
    return '';
  }
  return guestExpiresAt.value.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
});

const guestDaysLeft = computed(() => {
  if (!guestExpiresAt.value) {
    return '';
  }
  const diffMs = guestExpiresAt.value.getTime() - now.value;
  if (diffMs <= 0) {
    return 'expired';
  }
  const totalDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
  return `${totalDays} day${totalDays === 1 ? '' : 's'}`;
});

const ensureNotMigrating = () => {
  if (!isMigrating.value) {
    return true;
  }
  const t = (window as any).toastr;
  if (t?.info) {
    t.info('Guest migration in progress. Save/load is temporarily disabled.');
  }
  return false;
};

const clearSuccessCloseTimer = () => {
  if (successCloseTimer !== null) {
    window.clearTimeout(successCloseTimer);
    successCloseTimer = null;
  }
};

const clearBackupCloseTimer = () => {
  if (backupCloseTimer !== null) {
    window.clearTimeout(backupCloseTimer);
    backupCloseTimer = null;
  }
};

const handleAuthError = (err: any) => {
  const status = err?.status;
  if (status === 401) {
    window.location.assign('/login');
  } else if (status === 503) {
    redirectToWorkerRequired();
  }
};

const openOperationModal = (title: string, subtitle: string, detail: string) => {
  clearSuccessCloseTimer();
  if (savesModalOpen.value) {
    restoreGameSavesModal.value = true;
    savesModalOpen.value = false;
  }
  if (!operationModal.pauseToken) {
    operationModal.pauseToken = pauseBootstrapModals();
  }
  operationModal.open = true;
  operationModal.title = title;
  operationModal.subtitle = subtitle;
  operationModal.detail = detail;
  operationModal.statusText = 'Starting...';
  operationModal.progress = 0;
  operationModal.variant = 'info';
  operationModal.closable = false;
};

const closeOperationModal = () => {
  clearSuccessCloseTimer();
  operationModal.open = false;
  restoreBootstrapModals(operationModal.pauseToken);
  operationModal.pauseToken = null;
  if (backupModal.pending) {
    backupModal.pending = false;
    backupModal.open = true;
    clearBackupCloseTimer();
    backupCloseTimer = window.setTimeout(() => {
      if (backupModal.open) {
        closeBackupModal();
      }
    }, 6000);
    return;
  }
  if (restoreGameSavesModal.value && !backupModal.open) {
    savesModalOpen.value = true;
    restoreGameSavesModal.value = false;
  }
};

const closeBackupModal = () => {
  clearBackupCloseTimer();
  backupModal.open = false;
  restoreBootstrapModals(backupModal.pauseToken);
  backupModal.pauseToken = null;
  if (restoreGameSavesModal.value && !operationModal.open) {
    savesModalOpen.value = true;
    restoreGameSavesModal.value = false;
  }
};

const closeSavesModal = () => {
  savesModalOpen.value = false;
};

const sanitizeZipPath = (value: string) => {
  if (!value) {
    return '';
  }
  const marker = 'Backup saved to:';
  const index = value.indexOf(marker);
  const trimmed = (index >= 0 ? value.slice(index + marker.length) : value).trim();
  return trimmed.replace(/^["']|["']$/g, '');
};

const showBackupModal = (zipPath: string, gameId: number | null) => {
  backupModal.zipPath = sanitizeZipPath(zipPath);
  backupModal.gameId = gameId;
  backupModal.pending = true;
  if (!operationModal.open) {
    backupModal.pending = false;
    if (!backupModal.pauseToken) {
      backupModal.pauseToken = pauseBootstrapModals();
    }
    backupModal.open = true;
    clearBackupCloseTimer();
    backupCloseTimer = window.setTimeout(() => {
      if (backupModal.open) {
        closeBackupModal();
      }
    }, 6000);
  }
};

const isBackupLabel = (label: string) => {
  const normalized = label.toLowerCase();
  return normalized.includes('backup') || normalized.includes('backing up') || normalized.includes('back up');
};

const isMissingSaveMessage = (message: string) => {
  if (!message) {
    return false;
  }
  const normalized = message.toLowerCase();
  return (
    normalized.includes('save directory is empty')
    || normalized.includes('no files to save')
    || normalized.includes("don't have any save files")
  );
};

const extractZipPath = (response: any) => {
  const payload = response?.data ?? response;
  const result = payload?.result_data;
  if (result?.zip_path) {
    return sanitizeZipPath(result.zip_path);
  }
  const message = result?.message || '';
  if (typeof message === 'string') {
    return sanitizeZipPath(message);
  }
  return '';
};

const normalizeOperationIds = (data: any) => {
  if (!data) {
    return [];
  }
  if (Array.isArray(data.operation_ids)) {
    return data.operation_ids;
  }
  if (data.operation_id) {
    return [data.operation_id];
  }
  return [];
};

const calculatePercent = (progress: any) => {
  if (!progress) {
    return null;
  }
  if (progress.percentage !== undefined && progress.percentage !== null) {
    return Number(progress.percentage);
  }
  if (progress.total && progress.current !== undefined) {
    return Math.round((Number(progress.current) / Number(progress.total)) * 100);
  }
  return null;
};

const pollOperations = async (
  operationIds: string[],
  label: string,
  detail: string,
  onSuccess?: () => void | Promise<void>
) => {
  const ids = operationIds.filter(Boolean);
  if (ids.length === 0) {
    return;
  }

  openOperationModal(label, 'Working on your request.', detail);
  const maxAttempts = 300;
  let attempts = 0;
  let completed = false;
  let errorToastShown = false;

  while (!completed && attempts < maxAttempts) {
    attempts += 1;
    try {
      const results = await Promise.all(
        ids.map(async (id) => {
          try {
            const response = await store.checkOperationStatus(id);
            return response?.data || response;
          } catch {
            return { failed: true };
          }
        })
      );

      const totalCount = results.length;
      const completedCount = results.filter((item) => item?.completed).length;
      const failedCount = results.filter((item) => item?.failed).length;
      const resolvedCount = completedCount + failedCount;
      const progressValues = results
        .map((item) => calculatePercent(item?.progress))
        .filter((value) => typeof value === 'number');

      if (progressValues.length > 0) {
        const average = Math.round(progressValues.reduce((sum, value) => sum + value, 0) / progressValues.length);
        operationModal.progress = Math.min(100, Math.max(0, average));
      } else {
        operationModal.progress = Math.round((completedCount / totalCount) * 100);
      }

      const latestMessage = results
        .map((item) => item?.progress?.message || item?.message)
        .find((msg) => msg);
      const serverSuccessMessage = results
        .map((item) => item?.message || item?.result_data?.message)
        .find((msg) => msg);

      const displayStatus = isMissingSaveMessage(latestMessage || '') ? '' : (latestMessage || 'Processing...');
      operationModal.statusText = displayStatus || 'Processing...';
      operationModal.detail = `${completedCount}/${totalCount} completed`;

      if (resolvedCount === totalCount) {
        completed = true;
        if (failedCount === 0) {
          const successDetail = serverSuccessMessage || '';
          operationModal.variant = 'success';
          operationModal.statusText = serverSuccessMessage || 'All operations complete';
          operationModal.detail = successDetail;
          if (successDetail) {
            notify.success(successDetail);
          }
          const normalizedLabel = label.toLowerCase();
          const isBackup = isBackupLabel(label);
          if (normalizedLabel.includes('save') && !isBackup) {
            try {
              await refreshGames();
            } catch {
              // Ignore refresh errors to avoid blocking success flow.
            }
          }
          if (isBackup) {
            let zipPath = '';
            const backupResult = results.find((item) => item?.result_data?.zip_path);
            if (backupResult?.result_data?.zip_path) {
              zipPath = backupResult.result_data.zip_path;
            } else {
              try {
                const backupStatuses = await Promise.all(
                  operationIds.map(async (id) => store.checkOperationStatus(id))
                );
                zipPath = backupStatuses.map(extractZipPath).find((path) => path) || '';
              } catch {
                zipPath = '';
              }
            }
            if (zipPath) {
              showBackupModal(zipPath, selectedGameId.value);
            }
          }
          if (onSuccess) {
            try {
              await onSuccess();
            } catch {
              // Ignore refresh errors to avoid blocking success flow.
            }
          }
          successCloseTimer = window.setTimeout(() => {
            if (operationModal.open && operationModal.variant === 'success') {
              closeOperationModal();
            }
          }, 1500);
        } else if (failedCount < totalCount) {
          operationModal.variant = 'warning';
          operationModal.statusText = 'Partially complete';
          operationModal.detail = `${totalCount - failedCount} succeeded, ${failedCount} failed.`;
        } else {
          const errorMessage = results.find((item) => item?.message)?.message || '';
          operationModal.variant = 'danger';
          operationModal.statusText = 'Operation failed';
          const missingSave = isMissingSaveMessage(errorMessage);
          operationModal.detail = missingSave ? '' : errorMessage;
          notify.error(errorMessage || 'Operation failed.');
          errorToastShown = true;
          if (missingSave) {
            closeOperationModal();
          }
        }
        operationModal.progress = 100;
        operationModal.closable = true;
      } else {
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
    } catch (err) {
      operationModal.variant = 'danger';
      operationModal.statusText = 'Operation failed';
      operationModal.detail = '';
      operationModal.progress = 100;
      operationModal.closable = true;
      completed = true;
    }
  }

  if (!completed) {
    operationModal.variant = 'warning';
    operationModal.statusText = 'Still running';
    operationModal.detail = 'This is taking longer than expected. You can close this and check later.';
    operationModal.progress = Math.min(operationModal.progress, 99);
    operationModal.closable = true;
  }
};


const runSearch = async (query: string, sort: string) => {
  const requestId = ++searchRequestId;
  searching.value = true;
  try {
    await store.searchGames(query, sort);
  } catch (err: any) {
    await handleAuthError(err);
  } finally {
    if (requestId === searchRequestId) {
      searching.value = false;
    }
  }
};

const refreshGames = async () => {
  const query = searchQuery.value.trim();
  if (!query) {
    await refreshGames();
    return;
  }
  await runSearch(query, sortBy.value);
};

const onSearch = async ({ query, sort }: { query: string; sort: string }) => {
  if (!query.trim()) {
    await store.loadDashboard();
    return;
  }
  await runSearch(query, sort);
};

const scrollToAvailableGames = () => {
  const section = document.getElementById('availableGamesSection');
  if (section) {
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
};

const onRecentSelect = async (item: { title?: string }) => {
  const query = item?.title?.trim() || '';
  if (!query) {
    return;
  }
  if (searchQuery.value === query) {
    searchQuery.value = '';
    await nextTick();
  }
  searchQuery.value = query;
  scrollToAvailableGames();
};

const onOpenGame = (game: { id: number; title?: string }) => {
  selectedGameTitle.value = game?.title || '';
  selectedGameId.value = game?.id || null;
  loadSaveFolders();
  savesModalOpen.value = true;
};

const onSaveGame = async (game: { id: number; title?: string }) => {
  if (!ensureNotMigrating()) {
    return;
  }
  try {
    savingGameId.value = game.id;
    const data = await store.saveGame(game.id);
    const operationIds = normalizeOperationIds(data);
    await pollOperations(
      operationIds,
      'Saving game',
      `Saving ${game?.title || 'game'}...`,
      () => store.touchRecentGame(game.id)
    );
  } catch (err: any) {
    await handleAuthError(err);
  } finally {
    if (savingGameId.value === game.id) {
      savingGameId.value = null;
    }
  }
};

const onQuickLoadGame = async (game: { id: number; title?: string }) => {
  if (!ensureNotMigrating()) {
    return;
  }
  try {
    loadingGameId.value = game.id;
    const data = await store.loadGame(game.id);
    const operationIds = normalizeOperationIds(data);
    await pollOperations(operationIds, 'Loading game', `Loading ${game?.title || 'game'}...`);
  } catch (err: any) {
    await handleAuthError(err);
  } finally {
    if (loadingGameId.value === game.id) {
      loadingGameId.value = null;
    }
  }
};

const goToSettings = () => window.location.assign('/settings');
const goToProfile = () => window.location.assign('/settings');
const onLogout = async () => {
  authStore.suppressWorkerRedirect = true;
  try {
    await authStore.logout();
  } catch {
    // ignore
  } finally {
    window.location.assign('/login');
  }
};

const loadVersion = async () => {
  await metaStore.loadVersion();
};

useWorkerStatusSocket({
  userRef: computed(() => authStore.user),
  suppressRedirectRef,
  getWsToken: () => getSharedWsToken(),
  onWorkerUnavailable: () => {
    redirectToWorkerRequired();
  }
});

const loadSaveFolders = async () => {
  if (!selectedGameId.value) {
    saveFolders.value = [];
    saveFoldersError.value = '';
    return;
  }
  saveFoldersLoading.value = true;
  saveFoldersError.value = '';
  saveFolders.value = [];
  try {
    const data = await store.listSaveFolders(selectedGameId.value);
    saveFolders.value = data?.save_folders || [];
  } catch (err: any) {
    saveFoldersError.value = err?.message || '';
  } finally {
    saveFoldersLoading.value = false;
  }
};

const onLoadSaveFolder = async (folder: { folder_number: number }) => {
  if (!ensureNotMigrating()) {
    return;
  }
  if (!selectedGameId.value) {
    return;
  }
  try {
    const data = await store.loadGameSaveFolder(selectedGameId.value, folder.folder_number);
    const operationIds = normalizeOperationIds(data);
    await pollOperations(operationIds, 'Loading game', `Loading save ${folder.folder_number}...`);
  } catch (err: any) {
    await handleAuthError(err);
  }
};

const onDeleteSaveFolder = async (folder: { folder_number: number }) => {
  if (!ensureNotMigrating()) {
    return;
  }
  if (!selectedGameId.value) {
    return;
  }
  const confirmed = await requestConfirm({
    title: 'Delete Save',
    message: `Delete save ${folder.folder_number}? This cannot be undone.`,
    confirmText: 'Delete',
    variant: 'danger'
  });
  if (!confirmed) {
    return;
  }
  try {
    const data = await store.deleteSaveFolder(selectedGameId.value, folder.folder_number);
    const operationIds = normalizeOperationIds(data);
    await pollOperations(
      operationIds,
      'Deleting save',
      `Deleting save ${folder.folder_number}...`,
      loadSaveFolders
    );
  } catch (err: any) {
    await handleAuthError(err);
  }
};

const onBackupAllSaves = async () => {
  if (!ensureNotMigrating()) {
    return;
  }
  if (!selectedGameId.value) {
    return;
  }
  try {
    const data = await store.backupAllSaves(selectedGameId.value);
    const operationIds = normalizeOperationIds(data);
    await pollOperations(operationIds, 'Backing up saves', 'Creating backup...');
  } catch (err: any) {
    await handleAuthError(err);
  }
};

const onDeleteAllSaves = async () => {
  if (!ensureNotMigrating()) {
    return;
  }
  if (!selectedGameId.value) {
    return;
  }
  const confirmed = await requestConfirm({
    title: 'Delete Older Saves',
    message: 'Delete older saves for this game? The latest save will be kept.',
    confirmText: 'Delete',
    variant: 'danger'
  });
  if (!confirmed) {
    return;
  }
  try {
    const data = await store.deleteAllSaves(selectedGameId.value);
    const operationIds = normalizeOperationIds(data);
    await pollOperations(
      operationIds,
      'Deleting saves',
      'Deleting older saves...',
      loadSaveFolders
    );
  } catch (err: any) {
    await handleAuthError(err);
    if (err?.message) {
      notify.error(err.message);
    }
  }
};

const onOpenSaveLocation = async () => {
  if (!ensureNotMigrating()) {
    return;
  }
  if (!selectedGameId.value) {
    return;
  }
  try {
    const data = await store.openSaveLocation(selectedGameId.value);
    if (data?.message) {
      notify.success(data.message);
    }
  } catch (err: any) {
    await handleAuthError(err);
  }
};

const onDeleteGame = async () => {
  if (!selectedGameId.value) {
    return;
  }
  const confirmed = await requestConfirm({
    title: 'Delete Game',
    message: 'Delete this game and all its saves? This cannot be undone.',
    confirmText: 'Delete',
    variant: 'danger'
  });
  if (!confirmed) {
    return;
  }
  try {
    const data = await store.deleteGame(selectedGameId.value);
    const operationIds = normalizeOperationIds(data);
    savesModalOpen.value = false;
    const resetSelection = () => {
      selectedGameId.value = null;
      selectedGameTitle.value = '';
      saveFolders.value = [];
    };
    if (operationIds.length) {
      await pollOperations(
        operationIds,
        'Deleting game',
        `Deleting ${selectedGameTitle.value || 'game'}...`,
        async () => {
          resetSelection();
          await refreshGames();
        }
      );
    } else {
      resetSelection();
      await refreshGames();
    }
  } catch (err: any) {
    await handleAuthError(err);
  }
};

const onOpenBackupLocation = async () => {
  const zipPath = sanitizeZipPath(backupModal.zipPath);
  if (!zipPath || !backupModal.gameId) {
    return;
  }
  try {
    const data = await store.openBackupLocation(backupModal.gameId, zipPath);
    if (data?.message) {
      notify.success(data.message);
    }
    closeBackupModal();
  } catch (err: any) {
    await handleAuthError(err);
  }
};

const onEditGame = () => {
  if (!selectedGameId.value) {
    return;
  }
  savesModalOpen.value = false;
  window.location.assign(`/games/${selectedGameId.value}`);
};

onMounted(async () => {
  now.value = Date.now();
  bannerTimer = window.setInterval(() => {
    now.value = Date.now();
  }, 60000);
  try {
    await authStore.refreshUser();
    await store.loadDashboard();
  } catch (err: any) {
    await handleAuthError(err);
  }
});

onBeforeUnmount(() => {
  clearBackupCloseTimer();
  if (bannerTimer) {
    clearInterval(bannerTimer);
    bannerTimer = null;
  }
});
</script>

<style scoped>
.guest-expiry-banner {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.85rem 1.1rem;
  border-radius: 14px;
  border: 1px solid var(--white-opacity-10);
  background: rgba(46, 56, 76, 0.9);
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.25);
}

.guest-expiry-banner__icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: var(--primary-opacity-20);
  color: var(--color-primary);
  font-size: 1.1rem;
}

.guest-expiry-banner__content {
  flex: 1;
  min-width: 0;
}

.guest-expiry-banner__title {
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--color-white);
}

.guest-expiry-banner__meta {
  margin-top: 0.2rem;
  color: var(--white-opacity-60);
  font-size: 0.9rem;
}

.guest-expiry-banner__cta {
  border: 1px solid rgba(255, 255, 255, 0.4);
  background: rgba(0, 0, 0, 0.25);
  color: var(--color-white);
  font-weight: 600;
  padding: 0.45rem 0.85rem;
  border-radius: 999px;
  transition: all 0.2s ease;
}

.guest-expiry-banner__cta:hover {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--primary-opacity-20);
}

@media (max-width: 720px) {
  .guest-expiry-banner {
    flex-direction: column;
    align-items: flex-start;
  }

  .guest-expiry-banner__cta {
    width: 100%;
    text-align: center;
  }
}
</style>
