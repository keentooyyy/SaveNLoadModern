<template>
  <p class="text-white fs-6 text-center auth-footer" :class="textClass">
    <slot name="prefix">{{ prefix }}</slot>
    <RouterLink :to="to" class="text-secondary text-decoration-none fs-6" :tabindex="tabindex">
      {{ linkText }}
    </RouterLink>
  </p>
</template>

<script setup lang="ts">
defineProps({
  prefix: { type: String, default: '' },
  linkText: { type: String, required: true },
  to: { type: [String, Object], required: true },
  textClass: { type: String, default: '' },
  tabindex: { type: [Number, String], default: undefined }
});
</script>
