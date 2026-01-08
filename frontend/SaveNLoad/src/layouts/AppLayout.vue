<template>
  <div>
    <div class="d-none d-lg-block">
      <SidebarNav
        :version-label="versionLabel"
        :on-logout="onLogout"
        :on-load-version="onLoadVersion"
      />
    </div>
    <div class="main-content">
      <slot />
    </div>
    <div class="d-lg-none">
      <SidebarNav
        sidebar-id="sidebarMobile"
        :show-close="true"
        :version-label="versionLabel"
        :on-logout="onLogout"
        :on-load-version="onLoadVersion"
      />
    </div>
    <ConfirmModal />
  </div>
</template>

<script setup lang="ts">
import SidebarNav from '@/components/organisms/SidebarNav.vue';
import ConfirmModal from '@/components/organisms/ConfirmModal.vue';

defineProps({
  versionLabel: { type: String, default: '' },
  onLogout: { type: Function, default: null },
  onLoadVersion: { type: Function, default: null }
});
</script>

<style scoped>
@media (min-width: 992px) {
  :global(.offcanvas-backdrop) {
    display: none !important;
  }

  .main-content {
    margin-left: var(--sidebar-width);
  }
}
</style>
