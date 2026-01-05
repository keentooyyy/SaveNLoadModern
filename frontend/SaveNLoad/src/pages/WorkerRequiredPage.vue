<template>
  <BareLayout>
    <div class="container d-flex align-items-center justify-content-center min-vh-80">
      <div class="text-center w-100 max-width-600">
        <div class="mb-4">
          <img src="/images/icon.png" alt="Worker Missing" width="80" height="80" />
        </div>
        <h2 class="text-white mb-3">Worker Missing</h2>
        <p class="text-white-50 mb-4">To use the application you need to have a client worker running.</p>

        <div class="p-3 mb-4 rounded d-flex align-items-start worker-id-hint">
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
                    Claimed by: {{ worker.linked_user || 'Unknown' }}
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
            <div class="spinner-border text-white spinner-lg" role="status">
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
import { useRouter } from 'vue-router';
import { useWorkerListSocket } from '@/composables/useWorkerListSocket';

const API_BASE = import.meta.env.VITE_API_BASE;
const router = useRouter();
const { workers, supportsWebSocket } = useWorkerListSocket({ reloadOnClose: false });

const claimingId = ref<string | null>(null);
const hasShownSingleAvailableToast = ref(false);
const hasLoadedSnapshot = ref(false);

const hasWorkers = computed(() => workers.value.length > 0);
const availableWorkers = computed(() => workers.value.filter(worker => !worker.claimed));

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

const getCookie = (name: string) => {
  const match = document.cookie.match(new RegExp(`(^|;\\s*)${name}=([^;]*)`));
  return match ? decodeURIComponent(match[2]) : '';
};

const ensureCsrf = async () => {
  const token = getCookie('csrftoken');
  if (token) {
    return token;
  }
  await fetch(`${API_BASE}/auth/csrf`, { credentials: 'include' });
  return getCookie('csrftoken');
};

const fetchWorkersSnapshot = async () => {
  if (hasLoadedSnapshot.value) {
    return;
  }
  hasLoadedSnapshot.value = true;
  try {
    const response = await fetch(`${API_BASE}/api/client/unpaired/`, { credentials: 'include' });
    const data = await response.json().catch(() => null);
    if (response.ok && data?.workers) {
      workers.value = data.workers;
    }
  } catch {
    // Ignore snapshot errors; WS can still update later.
  }
};

const claimWorker = async (clientId: string) => {
  if (claimingId.value) {
    return;
  }

  try {
    claimingId.value = clientId;
    const csrfToken = await ensureCsrf();
    const response = await fetch(`${API_BASE}/api/client/claim/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      credentials: 'include',
      body: JSON.stringify({ client_id: clientId })
    });

    let data: any = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    if (!response.ok) {
      throw new Error(data?.error || data?.message || 'Failed to claim worker.');
    }

    notify.success(data?.message || 'Worker claimed successfully.');
    try {
      window.localStorage.setItem('savenload_client_id', clientId);
    } catch {
      // Ignore storage errors (private mode, etc.)
    }
    await router.push('/dashboard');
  } catch (error: any) {
    notify.error(error?.message || 'An error occurred. Please try again.');
  } finally {
    claimingId.value = null;
  }
};

const refreshList = () => {
  window.location.reload();
};

watch(availableWorkers, (available) => {
  if (available.length === 1 && !hasShownSingleAvailableToast.value) {
    notify.info('One worker available. Select it to connect.');
    hasShownSingleAvailableToast.value = true;
  } else if (available.length !== 1) {
    hasShownSingleAvailableToast.value = false;
  }
});

watch(supportsWebSocket, (supported) => {
  if (!supported) {
    notify.error('WebSockets are not available in this browser.');
    fetchWorkersSnapshot();
  }
});

onMounted(async () => {
  if (!workers.value.length) {
    await fetchWorkersSnapshot();
  }
});
</script>

<style scoped>
.worker-id-hint {
  background-color: var(--primary-opacity-15);
  border: 1px solid var(--primary-opacity-30);
  color: var(--color-primary-bootstrap);
}

.min-vh-80 {
  min-height: 80vh;
}

.max-width-600 {
  max-width: 600px;
}

.spinner-lg {
  width: 3rem;
  height: 3rem;
}
</style>
