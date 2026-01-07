<template>
  <div class="text-center py-3" :class="wrapperClass">
    <p class="text-white-50 mb-0">{{ message }}</p>
  </div>
</template>

<script setup lang="ts">
defineProps({
  message: { type: String, required: true },
  wrapperClass: { type: String, default: '' }
});
</script>
