<template>
  <AppLayout>
    <div class="container-fluid px-0">
      <PageHeader title="Home" />
      <RecentList :items="recentGames" :loading="recentLoading" @select="onRecentSelect" />
      <GameGrid
        v-model:search="searchQuery"
        v-model:sort="sortBy"
        :games="games"
        :loading="gamesLoading"
        @search="onSearch"
        @open="onOpenGame"
        @save="onSaveGame"
        @load="onQuickLoadGame"
      />
    </div>
  </AppLayout>
  <GameSavesModal :title="selectedGameTitle" />
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
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import PageHeader from '@/components/organisms/PageHeader.vue';
import RecentList from '@/components/organisms/RecentList.vue';
import GameGrid from '@/components/organisms/GameGrid.vue';
import GameSavesModal from '@/components/organisms/GameSavesModal.vue';
import OperationProgressModal from '@/components/organisms/OperationProgressModal.vue';
import AppLayout from '@/layouts/AppLayout.vue';
import { useDashboardStore } from '@/stores/dashboard';
import { useWorkerStatusSocket } from '@/composables/useWorkerStatusSocket';

const router = useRouter();
const store = useDashboardStore();

const searchQuery = ref('');
const sortBy = ref('name_asc');

const games = computed(() => store.games);
const recentGames = computed(() => store.recentGames);
const recentLoading = computed(() => store.loading && recentGames.value.length === 0);
const gamesLoading = computed(() => store.loading && games.value.length === 0);
const selectedGameTitle = ref('');

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

const handleAuthError = async (err: any) => {
  const status = err?.status;
  if (status === 401) {
    await router.push('/login');
  } else if (status === 503) {
    await router.push('/worker-required');
  }
};

const openOperationModal = (title: string, subtitle: string, detail: string) => {
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
  operationModal.open = false;
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

const pollOperations = async (operationIds: string[], label: string, detail: string) => {
  const ids = operationIds.filter(Boolean);
  if (ids.length === 0) {
    return;
  }

  openOperationModal(label, 'Working on your request.', detail);
  const maxAttempts = 300;
  let attempts = 0;
  let completed = false;

  while (!completed && attempts < maxAttempts) {
    attempts += 1;
    try {
      const results = await Promise.all(
        ids.map(async (id) => {
          try {
            const response = await store.checkOperationStatus(id);
            return response?.data || response;
          } catch (err) {
            return { failed: true, message: 'Failed to check status.' };
          }
        })
      );

      const totalCount = results.length;
      const completedCount = results.filter((item) => item?.completed).length;
      const failedCount = results.filter((item) => item?.failed).length;
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

      operationModal.statusText = latestMessage || 'Processing...';
      operationModal.detail = `${completedCount}/${totalCount} completed`;

      if (completedCount === totalCount) {
        completed = true;
        if (failedCount === 0) {
          operationModal.variant = 'success';
          operationModal.statusText = 'All operations complete';
          operationModal.detail = label.includes('Load') ? 'Game loaded successfully.' : 'Game saved successfully.';
          notify.success(operationModal.detail);
        } else if (failedCount < totalCount) {
          operationModal.variant = 'warning';
          operationModal.statusText = 'Partially complete';
          operationModal.detail = `${totalCount - failedCount} succeeded, ${failedCount} failed.`;
          notify.error('Some operations failed. Check your saves for details.');
        } else {
          const errorMessage = results.find((item) => item?.message)?.message || 'Operation failed.';
          operationModal.variant = 'danger';
          operationModal.statusText = 'Operation failed';
          operationModal.detail = errorMessage;
          notify.error(errorMessage);
        }
        operationModal.progress = 100;
        operationModal.closable = true;
      } else {
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
    } catch (err) {
      operationModal.variant = 'danger';
      operationModal.statusText = 'Operation failed';
      operationModal.detail = 'Unable to read operation status.';
      operationModal.progress = 100;
      operationModal.closable = true;
      notify.error('Unable to read operation status.');
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

useWorkerStatusSocket({
  onWorkerUnavailable: async () => {
    await router.push('/worker-required');
  }
});

const onSearch = async ({ query, sort }: { query: string; sort: string }) => {
  try {
    await store.searchGames(query, sort);
  } catch (err: any) {
    await handleAuthError(err);
  }
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

const onOpenGame = (game: { title?: string }) => {
  selectedGameTitle.value = game?.title || '';
  const modalEl = document.getElementById('gameSavesModal');
  const bootstrapModal = (window as any)?.bootstrap?.Modal?.getOrCreateInstance(modalEl);
  if (bootstrapModal) {
    bootstrapModal.show();
  }
};

const onSaveGame = async (game: { id: number; title?: string }) => {
  try {
    const data = await store.saveGame(game.id);
    const operationIds = normalizeOperationIds(data);
    await pollOperations(operationIds, 'Saving game', `Saving ${game?.title || 'game'}...`);
  } catch (err: any) {
    await handleAuthError(err);
  }
};

const onQuickLoadGame = async (game: { id: number; title?: string }) => {
  try {
    const data = await store.loadGame(game.id);
    const operationIds = normalizeOperationIds(data);
    await pollOperations(operationIds, 'Loading game', `Loading ${game?.title || 'game'}...`);
  } catch (err: any) {
    await handleAuthError(err);
  }
};

onMounted(async () => {
  try {
    await store.loadDashboard();
  } catch (err: any) {
    await handleAuthError(err);
  }
});
</script>
