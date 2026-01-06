<template>
  <aside
    :id="sidebarId"
    class="offcanvas offcanvas-start sidebar h-100 d-flex flex-column"
    tabindex="-1"
    aria-labelledby="sidebarLabel"
  >
    <div
      class="border-bottom border-secondary d-flex align-items-center justify-content-between p-2 p-md-3 gap-2 gap-md-3 sidebar-header-container"
    >
      <div class="d-flex align-items-center flex-grow-1 min-w-0 gap-2 gap-md-3 sidebar-header-content">
        <div class="d-flex align-items-center justify-content-center flex-shrink-0 logo-icon">
          <img src="/images/icon.png" alt="Save N Load" class="img-fluid" width="50" height="50" />
        </div>
        <span class="text-white fw-bold text-truncate fs-5 sidebar-header-text">Save N Load</span>
      </div>
      <button
        v-if="showClose"
        type="button"
        class="btn-close btn-close-white d-lg-none flex-shrink-0 ms-2"
        data-bs-dismiss="offcanvas"
        aria-label="Close"
      ></button>
    </div>

    <nav class="flex-grow-1 overflow-auto mt-3">
      <ul class="list-unstyled mb-0">
        <li class="mb-2">
          <RouterLink
            to="/dashboard"
            class="sidebar-nav-link d-flex align-items-center text-white text-decoration-none px-3 py-2 rounded"
            :class="{ active: isActive('/dashboard') }"
            @click="onDashboardClick"
          >
            <i class="fas fa-home me-2"></i>
            <span class="flex-grow-1">Home</span>
          </RouterLink>
        </li>
        <li class="mb-2">
          <RouterLink
            to="/settings"
            class="sidebar-nav-link d-flex align-items-center text-white text-decoration-none px-3 py-2 rounded"
            :class="{ active: isActive('/settings') }"
          >
            <i class="fas fa-cog me-2"></i>
            <span class="flex-grow-1">Settings</span>
          </RouterLink>
        </li>
      </ul>
    </nav>

    <div class="sidebar-footer border-top px-3 py-3">
      <div class="d-flex align-items-center justify-content-between mb-2">
        <span class="text-white-50 small fw-medium">{{ versionLabel }}</span>
      </div>
      <div class="d-flex align-items-center justify-content-between">
        <div class="text-white-50 small opacity-75">2026 SaveNLoadModern</div>
        <button class="btn p-0 text-white-50" type="button" title="Logout" aria-label="Logout" @click="onLogout">
          <i class="fas fa-sign-out-alt fs-4"></i>
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { useMetaStore } from '@/stores/meta';
import { useDashboardStore } from '@/stores/dashboard';
import { useRoute } from 'vue-router';

defineProps({
  sidebarId: { type: String, default: 'sidebar' },
  showClose: { type: Boolean, default: false }
});

const route = useRoute();
const router = useRouter();
const store = useAuthStore();
const metaStore = useMetaStore();
const dashboardStore = useDashboardStore();
const versionLabel = computed(() => metaStore.versionLabel);

const normalizeVersion = (raw: string) => {
  if (!raw) {
    return 'v--';
  }
  return raw.startsWith('v') ? raw : `v${raw}`;
};

const isActive = (path: string) => route.path === path;

const onDashboardClick = () => {
  if (isActive('/dashboard')) {
    window.dispatchEvent(new CustomEvent('dashboard:reset'));
  }
};

const onLogout = async () => {
  try {
    await store.logout();
  } finally {
    await router.push('/login');
  }
};

onMounted(async () => {
  if (dashboardStore.appVersion) {
    metaStore.setVersion(dashboardStore.appVersion);
    return;
  }
  await metaStore.loadVersion();
});
</script>

<style scoped>
.sidebar {
  width: var(--sidebar-width) !important;
  background-color: var(--sidebar-bg) !important;
}

.sidebar.offcanvas {
  --bs-offcanvas-width: var(--sidebar-width) !important;
  width: var(--sidebar-width) !important;
  background-color: var(--sidebar-bg) !important;
}

.sidebar.offcanvas.offcanvas-start {
  width: var(--sidebar-width) !important;
}

@media (max-width: 767.98px) {
  .sidebar.offcanvas {
    --bs-offcanvas-width: 80% !important;
    width: 80% !important;
  }

  .sidebar.offcanvas.offcanvas-start {
    width: 80% !important;
  }
}

@media (min-width: 768px) and (max-width: 991.98px) {
  .sidebar.offcanvas {
    --bs-offcanvas-width: 320px !important;
    width: 320px !important;
    max-width: 320px !important;
  }

  .sidebar.offcanvas.offcanvas-start {
    width: 320px !important;
    max-width: 320px !important;
  }
}

@media (min-width: 992px) {
  .sidebar.offcanvas {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    height: 100vh !important;
    visibility: visible !important;
    transform: none !important;
    z-index: 1000 !important;
    border: none !important;
    max-width: var(--sidebar-width) !important;
  }

  .sidebar.offcanvas.show {
    transform: none !important;
  }
}

.sidebar-header-container {
  min-height: 70px;
  overflow: hidden;
}

.sidebar-header-content {
  overflow: hidden;
}

.sidebar-header-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 575.98px) {
  .sidebar-header-container {
    min-height: 60px;
    padding: 0.75rem 1rem !important;
  }
}

@media (max-width: 335px) {
  .sidebar-header-container {
    min-height: 50px !important;
    padding: 0.5rem 0.75rem !important;
    gap: 0.5rem !important;
  }

  .sidebar-header-content {
    gap: 0.5rem !important;
  }

  .sidebar .logo-icon img,
  .sidebar .logo-icon svg {
    max-width: 32px !important;
    min-width: 28px !important;
  }

  .sidebar-header-text {
    font-size: 1rem !important;
  }

  .sidebar-header-container .btn-close {
    margin-left: 0.25rem !important;
    padding: 0.25rem !important;
  }
}

.sidebar-nav-link {
  transition: background-color 0.2s;
  margin: 2px 8px;
}

.sidebar-nav-link:hover:not(.active) {
  background-color: var(--white-opacity-08) !important;
}

.sidebar-nav-link.active {
  background-color: var(--primary-opacity-15) !important;
  color: var(--color-primary) !important;
}

.sidebar-nav-link.active i {
  color: var(--color-primary) !important;
}

.sidebar-nav-link i {
  width: 20px;
  text-align: center;
  font-size: 0.9rem;
}

@media (max-width: 767.98px) {
  .sidebar .border-bottom span {
    font-size: 1.4rem !important;
  }

  .sidebar-nav-link {
    font-size: 1.1rem !important;
    padding: 0.875rem 1rem !important;
  }

  .sidebar-nav-link i {
    font-size: 1.1rem !important;
    width: 24px !important;
  }

  .sidebar-footer {
    font-size: 1rem !important;
  }

  .sidebar-footer .small {
    font-size: 0.95rem !important;
  }
}

.sidebar .logo-icon img,
.sidebar .logo-icon svg {
  max-width: 50px;
  min-width: 40px;
  object-fit: contain;
}
</style>
