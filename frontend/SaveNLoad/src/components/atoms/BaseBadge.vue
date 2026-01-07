<template>
  <span class="badge" :class="badgeClass">
    <slot />
  </span>
</template>

<script setup lang="ts">
defineProps({
  badgeClass: { type: String, default: '' }
});
</script>
