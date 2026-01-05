<template>
  <AppLayout>
    <div class="container-fluid px-0">
      <PageHeader title="Home" />
      <RecentList :items="recentGames" />
      <GameGrid v-model:search="searchQuery" v-model:sort="sortBy" :games="games" @search="onSearch" />
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import PageHeader from '@/components/organisms/PageHeader.vue';
import RecentList from '@/components/organisms/RecentList.vue';
import GameGrid from '@/components/organisms/GameGrid.vue';
import AppLayout from '@/layouts/AppLayout.vue';
import { useDashboardStore } from '@/stores/dashboard';
import { useWorkerStatusSocket } from '@/composables/useWorkerStatusSocket';

const router = useRouter();
const store = useDashboardStore();

const searchQuery = ref('');
const sortBy = ref('name_asc');

const games = computed(() => store.games);
const recentGames = computed(() => store.recentGames);

const handleAuthError = async (err: any) => {
  const status = err?.status;
  if (status === 401) {
    await router.push('/login');
  } else if (status === 503 && err?.data?.requires_worker) {
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

onMounted(async () => {
  try {
    await store.loadDashboard();
  } catch (err: any) {
    await handleAuthError(err);
  }
});
</script>
