<template>
  <AppLayout>
    <div class="container-fluid px-0">
      <PageHeader
        title="Home"
        :user-label="headerName"
        :user-role="headerRole"
        @profile="goToProfile"
        @settings="goToSettings"
        @logout="onLogout"
      />
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
    :title="selectedGameTitle"
    :save-folders="saveFolders"
    :loading="saveFoldersLoading"
    :error="saveFoldersError"
    :is-admin="isAdmin"
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
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import PageHeader from '@/components/organisms/PageHeader.vue';
import RecentList from '@/components/organisms/RecentList.vue';
import GameGrid from '@/components/organisms/GameGrid.vue';
import GameSavesModal from '@/components/organisms/GameSavesModal.vue';
import OperationProgressModal from '@/components/organisms/OperationProgressModal.vue';
import BackupCompleteModal from '@/components/organisms/BackupCompleteModal.vue';
import AppLayout from '@/layouts/AppLayout.vue';
import { useDashboardStore } from '@/stores/dashboard';
import { useAuthStore } from '@/stores/auth';
import { useConfirm } from '@/composables/useConfirm';

const router = useRouter();
const store = useDashboardStore();
const authStore = useAuthStore();
const { requestConfirm } = useConfirm();

const searchQuery = ref('');
const sortBy = ref('name_asc');

const games = computed(() => store.games);
const recentGames = computed(() => store.recentGames);
const recentLoading = computed(() => store.loading && recentGames.value.length === 0);
const gamesLoading = computed(() => store.loading && games.value.length === 0);
const isAdmin = computed(() => store.isAdmin);
const headerName = computed(() => store.user?.username || authStore.user?.username || '');
const headerRole = computed(() => (store.user?.role || authStore.user?.role || '').toUpperCase());
const selectedGameTitle = ref('');
const selectedGameId = ref<number | null>(null);
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
  closable: false
});

const backupModal = reactive({
  open: false,
  zipPath: '',
  gameId: null as number | null,
  pending: false
});
const restoreGameSavesModal = ref(false);

let successCloseTimer: number | null = null;
let backupCloseTimer: number | null = null;

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
  },
  info: (msg: string) => {
    const t = (window as any).toastr;
    if (t?.info) {
      t.info(msg);
    }
  }
};

const handleAuthError = async (err: any) => {
  const status = err?.status;
  if (status === 401) {
    await router.push('/login');
  } else if (status === 503) {
    await router.push('/worker-required');
  }
};

const openOperationModal = (title: string, subtitle: string, detail: string) => {
  clearSuccessCloseTimer();
  const modalEl = document.getElementById('gameSavesModal');
  if (modalEl?.classList.contains('show')) {
    restoreGameSavesModal.value = true;
    const bootstrapModal = (window as any)?.bootstrap?.Modal?.getOrCreateInstance(modalEl);
    bootstrapModal?.hide();
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
    const modalEl = document.getElementById('gameSavesModal');
    const bootstrapModal = (window as any)?.bootstrap?.Modal?.getOrCreateInstance(modalEl);
    bootstrapModal?.show();
    restoreGameSavesModal.value = false;
  }
};

const closeBackupModal = () => {
  clearBackupCloseTimer();
  backupModal.open = false;
  if (restoreGameSavesModal.value && !operationModal.open) {
    const modalEl = document.getElementById('gameSavesModal');
    const bootstrapModal = (window as any)?.bootstrap?.Modal?.getOrCreateInstance(modalEl);
    bootstrapModal?.show();
    restoreGameSavesModal.value = false;
  }
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
              await store.loadDashboard();
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


const onSearch = async ({ query, sort }: { query: string; sort: string }) => {
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

const scrollToAvailableGames = () => {
  const section = document.getElementById('availableGamesSection');
  if (section) {
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
};

const resetDashboardFilters = async () => {
  searchQuery.value = '';
  sortBy.value = 'name_asc';
  try {
    await store.loadDashboard();
  } catch {
    // Ignore refresh errors to avoid blocking navigation.
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
  const modalEl = document.getElementById('gameSavesModal');
  const bootstrapModal = (window as any)?.bootstrap?.Modal?.getOrCreateInstance(modalEl);
  if (bootstrapModal) {
    bootstrapModal.show();
  }
};

const onSaveGame = async (game: { id: number; title?: string }) => {
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

const goToSettings = () => router.push('/settings');
const goToProfile = () => router.push('/settings');
const onLogout = async () => {
  try {
    await authStore.logout();
  } catch {
    // ignore
  } finally {
    await router.push('/login');
  }
};

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
    const modalEl = document.getElementById('gameSavesModal');
    const bootstrapModal = (window as any)?.bootstrap?.Modal?.getOrCreateInstance(modalEl);
    bootstrapModal?.hide();
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
          await store.loadDashboard();
        }
      );
    } else {
      resetSelection();
      await store.loadDashboard();
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
  if (!router.hasRoute('game-detail')) {
    router.addRoute({
      name: 'game-detail',
      path: '/games/:id',
      component: () => import('@/pages/GameDetailPage.vue'),
      meta: { title: 'Game Details', requiresAuth: true }
    });
  }
  const modalEl = document.getElementById('gameSavesModal');
  const bootstrapModal = (window as any)?.bootstrap?.Modal?.getOrCreateInstance(modalEl);
  bootstrapModal?.hide();
  void router.push({ path: `/games/${selectedGameId.value}` });
};

onMounted(async () => {
  window.addEventListener('dashboard:reset', resetDashboardFilters);
  try {
    if (!store.dashboardLoaded) {
      await store.loadDashboard();
    }
  } catch (err: any) {
    await handleAuthError(err);
  }
});

onBeforeUnmount(() => {
  window.removeEventListener('dashboard:reset', resetDashboardFilters);
  clearBackupCloseTimer();
});
</script>
