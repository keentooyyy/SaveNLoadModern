<template>
  <div class="text-center">
    <div class="text-secondary small">{{ label }}</div>
    <div class="h4 mb-0">{{ value }}</div>
  </div>
</template>

<script setup lang="ts">
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true }
});
</script>
