<template>
  <CollapsibleCard
    title="Operation Queue Management"
    icon="fa-tasks"
    collapse-id="operationQueueCollapse"
    header-class="operation-queue-header"
    icon-class="operation-queue-icon"
    title-class="operation-queue-title"
    chevron-class="operation-queue-chevron"
    chevron-id="operationQueueChevron"
  >
    <div class="mb-4">
      <SectionTitle text="Queue Statistics" />
      <div class="text-white">
        <div v-if="loading" class="text-center py-3">
          <div class="spinner-border text-light" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
        </div>
        <div v-else-if="error" class="text-center py-3 text-white-50">{{ error }}</div>
        <div v-else class="d-flex flex-column gap-2">
          <div class="d-flex justify-content-between">
            <span>Total</span>
            <span class="fw-semibold">{{ stats.total }}</span>
          </div>
          <div class="d-flex justify-content-between">
            <span>Pending</span>
            <span>{{ stats.by_status.pending }}</span>
          </div>
          <div class="d-flex justify-content-between">
            <span>In Progress</span>
            <span>{{ stats.by_status.in_progress }}</span>
          </div>
          <div class="d-flex justify-content-between">
            <span>Completed</span>
            <span>{{ stats.by_status.completed }}</span>
          </div>
          <div class="d-flex justify-content-between">
            <span>Failed</span>
            <span>{{ stats.by_status.failed }}</span>
          </div>
        </div>
      </div>
    </div>

    <hr class="border-secondary my-4" />

    <div>
      <SectionTitle text="Clear Operations" />
      <IconButton
        type="button"
        variant="secondary"
        class="text-white fw-bold"
        icon="fa-trash"
        :disabled="loading"
        @click="clearAll"
      >
        Clear All Operations
      </IconButton>
    </div>
  </CollapsibleCard>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import CollapsibleCard from '@/components/molecules/CollapsibleCard.vue';
import IconButton from '@/components/atoms/IconButton.vue';
import SectionTitle from '@/components/atoms/SectionTitle.vue';
import { useSettingsStore } from '@/stores/settings';
import { useConfirm } from '@/composables/useConfirm';

const store = useSettingsStore();
const loading = ref(false);
const error = ref('');
const { requestConfirm } = useConfirm();
const stats = ref({
  total: 0,
  by_status: {
    pending: 0,
    in_progress: 0,
    completed: 0,
    failed: 0
  }
});

const loadStats = async () => {
  loading.value = true;
  error.value = '';
  try {
    const data = await store.queueStats();
    stats.value = data?.data || data || stats.value;
  } catch (err: any) {
    error.value = err?.message || '';
  } finally {
    loading.value = false;
  }
};

const clearAll = async () => {
  const confirmed = await requestConfirm({
    title: 'Clear Operations',
    message: 'Clear all operations?',
    confirmText: 'Clear',
    variant: 'danger'
  });
  if (!confirmed) {
    return;
  }
  await store.cleanupQueue('all');
  loadStats();
};

onMounted(() => {
  if (store.bootstrapStatsLoaded) {
    stats.value = store.queueStatsData;
    return;
  }
  loadStats();
});
</script>
