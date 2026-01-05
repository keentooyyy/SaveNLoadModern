<template>
  <div class="d-flex gap-2" :class="alignClass">
    <slot />
  </div>
</template>

<script setup lang="ts">
defineProps({
  alignClass: { type: String, default: '' }
});
</script>
