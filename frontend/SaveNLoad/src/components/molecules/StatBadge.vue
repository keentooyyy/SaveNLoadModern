<template>
  <div class="text-center">
    <div class="text-secondary small">{{ label }}</div>
    <BaseBadge badge-class="bg-transparent text-white h4 mb-0 p-0">{{ value }}</BaseBadge>
  </div>
</template>

<script setup lang="ts">
import BaseBadge from '@/components/atoms/BaseBadge.vue';

defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true }
});
</script>
