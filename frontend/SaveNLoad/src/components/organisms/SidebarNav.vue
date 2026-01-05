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
          <img src="/images/icon.png" alt="Save N Load" class="img-fluid" />
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
        <span class="text-white-50 small fw-medium">v1.0.0</span>
      </div>
      <div class="d-flex align-items-center justify-content-between">
        <div class="text-white-50 small opacity-75">Ac 2026 SaveNLoadModern</div>
        <button class="btn p-0 text-white-50" type="button" title="Logout" aria-label="Logout">
          <i class="fas fa-sign-out-alt fs-4"></i>
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router';

defineProps({
  sidebarId: { type: String, default: 'sidebar' },
  showClose: { type: Boolean, default: false }
});

const route = useRoute();

const isActive = (path: string) => route.path === path;
</script>
