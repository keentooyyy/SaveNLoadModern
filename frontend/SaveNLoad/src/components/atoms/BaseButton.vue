<template>
  <button :type="type" :class="classes">
    <slot />
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps({
  variant: { type: String, default: 'primary' },
  size: { type: String, default: '' },
  type: { type: String, default: 'button' }
});

const classes = computed(() => [
  'btn',
  `btn-${props.variant}`,
  props.size ? `btn-${props.size}` : ''
]);
</script>
