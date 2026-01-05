<template>
  <RouterLink :to="to" class="link-underline link-underline-opacity-0 link-underline-opacity-100-hover">
    <slot />
  </RouterLink>
</template>

<script setup lang="ts">
defineProps({
  to: { type: [String, Object], required: true }
});
</script>
