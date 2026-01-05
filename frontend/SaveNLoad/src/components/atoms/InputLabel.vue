<template>
  <label :for="forId" class="fs-6 opacity-50" :class="labelClass">
    <slot>{{ text }}</slot>
  </label>
</template>

<script setup lang="ts">
defineProps({
  forId: String,
  text: String,
  labelClass: { type: String, default: '' }
});
</script>
