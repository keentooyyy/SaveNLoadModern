<template>
  <button
    :type="type"
    class="btn"
    :class="[variantClass, sizeClass]"
    :disabled="disabled || loading"
    :tabindex="tabindex"
  >
    <i v-if="loading" class="fas fa-spinner fa-spin me-1" aria-hidden="true"></i>
    <i v-else-if="icon" class="fas" :class="[icon, iconClass, iconGapClass]"></i>
    <slot />
  </button>
</template>

<script setup lang="ts">
import { computed, useSlots } from 'vue';

const props = defineProps({
  type: { type: String, default: 'button' },
  variant: { type: String, default: 'secondary' },
  size: { type: String, default: '' },
  icon: { type: String, default: '' },
  iconClass: { type: String, default: '' },
  iconPosition: { type: String, default: 'left' },
  disabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  tabindex: { type: [Number, String], default: undefined }
});

const slots = useSlots();
const hasLabel = computed(() => Boolean(slots.default));
const variantClass = computed(() => `btn-${props.variant}`);
const sizeClass = computed(() => (props.size ? `btn-${props.size}` : ''));
const iconGapClass = computed(() => {
  if (!hasLabel.value) {
    return '';
  }
  return props.iconPosition === 'right' ? 'ms-1' : 'me-1';
});
</script>
