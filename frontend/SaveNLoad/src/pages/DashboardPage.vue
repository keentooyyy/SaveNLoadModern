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
      />
    </div>
  </AppLayout>
  <GameSavesModal :title="selectedGameTitle" />
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import PageHeader from '@/components/organisms/PageHeader.vue';
import RecentList from '@/components/organisms/RecentList.vue';
import GameGrid from '@/components/organisms/GameGrid.vue';
import GameSavesModal from '@/components/organisms/GameSavesModal.vue';
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

const handleAuthError = async (err: any) => {
  const status = err?.status;
  if (status === 401) {
    await router.push('/login');
  } else if (status === 503) {
    await router.push('/worker-required');
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

onMounted(async () => {
  try {
    await store.loadDashboard();
  } catch (err: any) {
    await handleAuthError(err);
  }
});
</script>
