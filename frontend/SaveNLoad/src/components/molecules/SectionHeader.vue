<template>
  <div class="d-flex flex-wrap align-items-center justify-content-between gap-3">
    <div>
      <h4 class="mb-1">{{ title }}</h4>
      <p v-if="subtitle" class="text-secondary mb-0">{{ subtitle }}</p>
    </div>
    <div class="d-flex gap-2">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps({
  title: String,
  subtitle: String
});
</script>
