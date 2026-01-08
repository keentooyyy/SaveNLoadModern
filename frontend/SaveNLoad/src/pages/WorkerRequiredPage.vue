<template>
  <BareLayout>
    <div v-if="isLoading" class="container d-flex align-items-center justify-content-center" style="min-height: 80vh;">
      <div class="text-center">
        <div class="spinner-border text-white" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
        <p class="text-white-50 mt-3 mb-0">Checking session...</p>
      </div>
    </div>
    <div v-else class="container d-flex align-items-center justify-content-center" style="min-height: 80vh;">
      <div class="text-center w-100" style="max-width: 600px;">
        <div class="mb-4">
          <img :src="iconUrl" alt="Worker Missing" width="80" height="80" />
        </div>
        <h2 class="text-white mb-3">Worker Missing</h2>
        <p class="text-white-50 mb-4">To use the application you need to have a client worker running.</p>

        <div class="p-3 mb-4 rounded d-flex align-items-start bg-primary bg-opacity-10 border border-primary text-white">
          <i class="fas fa-info-circle me-3 mt-1 fs-5"></i>
          <div>
            <strong>Tip:</strong> The correct Worker ID contains your PC name + a unique code.<br />
            Example: <code>YOUR-PC-NAME_a1:b2:c3:d4:e5:f6</code>
          </div>
        </div>

        <div v-if="hasWorkers" class="card bg-dark border-secondary">
          <div class="card-header border-secondary">
            <h5 class="mb-0 text-white">Online Workers</h5>
          </div>
          <div class="list-group list-group-flush">
            <div
              v-for="worker in workers"
              :key="worker.client_id"
              class="list-group-item bg-dark border-secondary d-flex justify-content-between align-items-center"
            >
              <div class="text-start">
                <strong class="text-white d-block">Worker ID: {{ worker.client_id }}</strong>
                <div class="mt-1">
                  <span class="badge bg-success">Online</span>
                  <span v-if="worker.claimed" class="badge bg-warning text-dark ms-2">
                    Claimed by: {{ worker.linked_user === authStore.user?.username ? 'You' : (worker.linked_user || 'Unknown') }}
                  </span>
                  <span v-else class="badge bg-secondary ms-2">Unclaimed</span>
                </div>
              </div>
              <button
                v-if="!worker.claimed"
                class="btn btn-primary btn-sm claim-btn"
                :disabled="claimingId === worker.client_id"
                @click="claimWorker(worker.client_id)"
              >
                {{ claimingId === worker.client_id ? 'CONNECTING...' : 'Use Worker' }}
              </button>
              <span v-else class="text-muted">Already claimed</span>
            </div>
          </div>
        </div>
        <div v-else class="card bg-dark border-secondary p-4 text-center">
          <div class="mb-3">
            <div class="spinner-border text-white" role="status" style="width: 3rem; height: 3rem;">
              <span class="visually-hidden">Loading...</span>
            </div>
          </div>
          <h5 class="text-white mb-2">Searching for Workers</h5>
          <p class="text-white-50 mb-0">Please ensure the SaveNLoad client is running on your PC.</p>
        </div>
        <button
          class="btn btn-outline-light mt-3"
          type="button"
          :class="{ 'd-none': hasWorkers }"
          @click="refreshList"
        >
          <i class="fas fa-sync-alt me-2"></i>Refresh List
        </button>
      </div>
    </div>
  </BareLayout>
</template>

<script setup lang="ts">
import BareLayout from '@/layouts/BareLayout.vue';
import { computed, onMounted, ref, watch } from 'vue';
import { useWorkerListSocket } from '@/composables/useWorkerListSocket';
import { useAuthStore } from '@/stores/auth';
import { apiPost } from '@/utils/apiClient';
import { notify } from '@/utils/notify';
import { getSharedWsToken } from '@/utils/wsToken';

const authStore = useAuthStore();
const { workers } = useWorkerListSocket({
  reloadOnClose: false,
  userRef: computed(() => authStore.user),
  getWsToken: () => getSharedWsToken()
});
const iconUrl = '/static/images/icon.png';
const isLoading = ref(true);

const claimingId = ref<string | null>(null);
const hasShownSingleAvailableToast = ref(false);
const redirecting = ref(false);
const localClientId = ref<string | null>(null);

const hasWorkers = computed(() => workers.value.length > 0);
const availableWorkers = computed(() => workers.value.filter(worker => !worker.claimed));
const claimedWorkerForUser = computed(() => {
  const username = authStore.user?.username;
  if (!username) {
    return null;
  }
  return workers.value.find((worker) => worker.claimed && worker.linked_user === username) || null;
});
const claimedWorkerForClient = computed(() => {
  const clientId = localClientId.value;
  if (!clientId) {
    return null;
  }
  return workers.value.find((worker) => worker.client_id === clientId && worker.claimed) || null;
});

const redirectIfClaimed = () => {
  if (redirecting.value) {
    return;
  }
  if (claimedWorkerForUser.value || claimedWorkerForClient.value) {
    redirecting.value = true;
    window.location.assign('/dashboard');
  }
};

const claimWorker = async (clientId: string) => {
  if (claimingId.value) {
    return;
  }

  try {
    claimingId.value = clientId;
    const data = await apiPost('/client/claim/', { client_id: clientId });
    if (data?.message) {
      notify.flashSuccess(data.message);
    }
    try {
      window.localStorage.setItem('savenload_client_id', clientId);
    } catch {
      // Ignore storage errors (private mode, etc.)
    }
    window.location.assign('/dashboard');
  } catch (error: any) {
    if (error?.message) {
      notify.error(error.message);
    }
  } finally {
    claimingId.value = null;
  }
};

const refreshList = () => {
  notify.flashInfo('Refreshing worker list...');
  window.location.reload();
};

watch(availableWorkers, (available) => {
  if (available.length === 1 && !hasShownSingleAvailableToast.value) {
    hasShownSingleAvailableToast.value = true;
  } else if (available.length !== 1) {
    hasShownSingleAvailableToast.value = false;
  }
});

onMounted(async () => {
  try {
    await authStore.refreshUser();
    if (!authStore.user) {
      window.location.assign('/login');
      return;
    }
    try {
      localClientId.value = window.localStorage.getItem('savenload_client_id');
    } catch {
      localClientId.value = null;
    }
    redirectIfClaimed();
  } catch {
    window.location.assign('/login');
    return;
  } finally {
    isLoading.value = false;
  }
});

watch([claimedWorkerForUser, claimedWorkerForClient], () => {
  redirectIfClaimed();
});

</script>

<style scoped>
</style>
