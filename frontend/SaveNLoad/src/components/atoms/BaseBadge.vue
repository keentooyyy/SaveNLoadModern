<template>
  <span :class="classes">
    <slot />
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps({
  variant: { type: String, default: 'secondary' }
});

const classes = computed(() => ['badge', `bg-${props.variant}`]);
</script>
