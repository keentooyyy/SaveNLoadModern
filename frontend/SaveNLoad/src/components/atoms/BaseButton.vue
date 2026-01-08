<template>
  <button
    :type="type"
    class="btn"
    :class="[variantClass, sizeClass, buttonClass]"
    :disabled="disabled"
    :tabindex="tabindex"
  >
    <slot />
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { PropType } from 'vue';

const props = defineProps({
  type: { type: String as PropType<'button' | 'submit' | 'reset'>, default: 'button' },
  variant: { type: String, default: 'secondary' },
  size: { type: String, default: '' },
  buttonClass: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  tabindex: { type: [Number, String], default: undefined }
});

const variantClass = computed(() => `btn-${props.variant}`);
const sizeClass = computed(() => (props.size ? `btn-${props.size}` : ''));
</script>
