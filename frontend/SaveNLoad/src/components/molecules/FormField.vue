<template>
  <div class="mb-3">
    <label v-if="label" class="form-label text-uppercase small text-secondary">{{ label }}</label>
    <slot />
    <div v-if="hint" class="form-text">{{ hint }}</div>
  </div>
</template>

<script setup lang="ts">
defineProps({
  label: String,
  hint: String
});
</script>
