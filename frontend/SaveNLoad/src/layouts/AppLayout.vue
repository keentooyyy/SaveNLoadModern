<template>
  <div>
    <div class="d-none d-lg-block">
      <SidebarNav />
    </div>
    <div class="main-content">
      <slot />
    </div>
    <div class="d-lg-none">
      <SidebarNav sidebar-id="sidebarMobile" :show-close="true" />
    </div>
  </div>
</template>

<script setup lang="ts">
import SidebarNav from '@/components/organisms/SidebarNav.vue';
</script>
