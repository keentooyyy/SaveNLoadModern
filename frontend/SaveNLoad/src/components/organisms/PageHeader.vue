<template>
  <div class="d-flex align-items-center shadow bg-primary py-3">
    <div class="d-flex align-items-center justify-content-between gap-3 w-100 px-4">
      <div class="d-flex align-items-center gap-3">
        <span
          class="text-white d-lg-none p-0 d-flex align-items-center"
          role="button"
          tabindex="0"
          data-bs-toggle="offcanvas"
          data-bs-target="#sidebarMobile"
          aria-controls="sidebarMobile"
          aria-label="Toggle sidebar"
        >
          <i class="fas fa-bars fs-3"></i>
        </span>
        <h6 class="text-white mb-0">{{ title }}</h6>
      </div>
      <div v-if="userLabel" class="text-white fs-6 fw-medium">Welcome, {{ userLabel }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps({
  title: { type: String, default: 'Page' },
  userLabel: { type: String, default: '' }
});
</script>

<style scoped>
</style>
