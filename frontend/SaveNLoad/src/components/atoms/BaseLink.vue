<template>
  <a
    :href="resolvedHref"
    :class="linkClass"
    :tabindex="tabindex"
  >
    <slot />
  </a>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps({
  to: { type: [String, Object], default: '' },
  href: { type: String, default: '' },
  linkClass: { type: String, default: '' },
  tabindex: { type: [Number, String], default: undefined }
});

const resolvedHref = computed(() => {
  if (props.href) {
    return props.href;
  }
  return typeof props.to === 'string' ? props.to : '';
});
</script>
