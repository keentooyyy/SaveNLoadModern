<template>
  <CollapsibleCard
    title="Worker Management"
    icon="fa-network-wired"
    collapse-id="workerManagementCollapse"
    header-class="worker-management-header"
    icon-class="worker-management-icon"
    title-class="worker-management-title"
    chevron-class="worker-management-chevron"
    chevron-id="workerManagementChevron"
  >
    <div class="d-flex flex-column flex-md-row justify-content-between gap-2 mb-3">
      <div class="text-white-50 small">
        Online workers are listed here. Use the kill switch to unpair all claims.
      </div>
      <div class="d-flex gap-2">
        <IconButton
          type="button"
          variant="outline-secondary"
          class="text-white"
          icon="fa-sync"
          :disabled="loading"
          @click="loadWorkers"
        >
          Refresh
        </IconButton>
        <IconButton
          type="button"
          variant="danger"
          class="text-white fw-bold"
          icon="fa-ban"
          :disabled="loading || !hasClaimedWorkers"
          :loading="isKilling"
          @click="onKillSwitch"
        >
          Kill Switch
        </IconButton>
      </div>
    </div>

    <LoadingState v-if="loading" />
    <EmptyState v-else-if="error" :message="error" />
    <EmptyState v-else-if="!workers.length" message="No online workers found." />
    <div v-else class="table-responsive">
      <table class="table table-dark table-hover align-middle mb-0 worker-table">
        <thead>
          <tr>
            <th scope="col" class="text-white-50">Worker ID</th>
            <th scope="col" class="text-white-50">Status</th>
            <th scope="col" class="text-white-50">Claimed By</th>
            <th scope="col" class="text-white-50">Last Ping</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="worker in workers" :key="worker.client_id">
            <td class="fw-semibold text-white">{{ worker.client_id }}</td>
            <td>
              <span class="badge bg-success">Online</span>
              <span
                v-if="worker.claimed"
                class="badge bg-warning text-dark ms-2"
              >
                Claimed
              </span>
              <span v-else class="badge bg-secondary ms-2">Unclaimed</span>
            </td>
            <td class="text-white-50">
              {{ worker.linked_user || '—' }}
            </td>
            <td class="text-white-50">
              {{ formatTimestamp(worker.last_ping_response) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </CollapsibleCard>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import CollapsibleCard from '@/components/molecules/CollapsibleCard.vue';
import IconButton from '@/components/atoms/IconButton.vue';
import LoadingState from '@/components/molecules/LoadingState.vue';
import EmptyState from '@/components/molecules/EmptyState.vue';
import { useConfirm } from '@/composables/useConfirm';

type WorkerSnapshot = {
  client_id: string;
  claimed: boolean;
  linked_user?: string | null;
  last_ping_response?: string | null;
};

const props = defineProps<{
  listWorkers: () => Promise<{ workers?: WorkerSnapshot[] } | void>;
  unclaimAllWorkers: () => Promise<{ workers?: WorkerSnapshot[] } | void>;
}>();

const { requestConfirm } = useConfirm();

const loading = ref(false);
const isKilling = ref(false);
const error = ref('');
const workers = ref<WorkerSnapshot[]>([]);
const hasClaimedWorkers = computed(() => workers.value.some(worker => worker.claimed));

const formatTimestamp = (value?: string | null) => {
  if (!value) {
    return '—';
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
};

const loadWorkers = async () => {
  loading.value = true;
  error.value = '';
  try {
    const data = await props.listWorkers();
    const next = (data as { workers?: WorkerSnapshot[] } | undefined)?.workers;
    if (next) {
      workers.value = next;
    }
  } catch (err: any) {
    error.value = err?.message || '';
  } finally {
    loading.value = false;
  }
};

const onKillSwitch = async () => {
  if (isKilling.value) {
    return;
  }
  const confirmed = await requestConfirm({
    title: 'Unpair All Workers',
    message: 'This will unpair every online worker from its current user. Continue?',
    confirmText: 'Unpair All',
    variant: 'danger'
  });
  if (!confirmed) {
    return;
  }
  isKilling.value = true;
  try {
    const data = await props.unclaimAllWorkers();
    const next = (data as { workers?: WorkerSnapshot[] } | undefined)?.workers;
    if (next) {
      workers.value = next;
    }
  } catch (err: any) {
    error.value = err?.message || '';
  } finally {
    isKilling.value = false;
  }
};

onMounted(() => {
  void loadWorkers();
});
</script>

<style scoped>
.worker-table {
  --bs-table-bg: transparent;
  --bs-table-border-color: var(--white-opacity-10);
  --bs-table-hover-bg: var(--white-opacity-08);
}

.worker-table th,
.worker-table td {
  border-color: var(--white-opacity-10);
}
</style>
