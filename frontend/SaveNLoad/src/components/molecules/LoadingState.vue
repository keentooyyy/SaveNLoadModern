<template>
  <div class="text-center py-3" :class="wrapperClass">
    <div class="spinner-border" :class="[spinnerClass, spinnerSizeClass]" role="status">
      <span class="visually-hidden">Loading...</span>
    </div>
    <p v-if="message" class="text-white-50 mt-2 mb-0">{{ message }}</p>
  </div>
</template>

<script setup lang="ts">
defineProps({
  message: { type: String, default: '' },
  spinnerClass: { type: String, default: 'text-light' },
  spinnerSizeClass: { type: String, default: '' },
  wrapperClass: { type: String, default: '' }
});
</script>
