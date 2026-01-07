<template>
  <component
    :is="componentType"
    :to="to"
    :href="href"
    :class="linkClass"
    :tabindex="tabindex"
  >
    <slot />
  </component>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { RouterLink } from 'vue-router';

const props = defineProps({
  to: { type: [String, Object], default: '' },
  href: { type: String, default: '' },
  linkClass: { type: String, default: '' },
  tabindex: { type: [Number, String], default: undefined }
});

const componentType = computed(() => (props.to ? RouterLink : 'a'));
</script>
