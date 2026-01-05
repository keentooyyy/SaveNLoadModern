<template>
  <h6 class="text-white mb-3 fw-bold" :class="titleClass">{{ text }}</h6>
</template>

<script setup lang="ts">
defineProps({
  text: { type: String, required: true },
  titleClass: { type: String, default: '' }
});
</script>
