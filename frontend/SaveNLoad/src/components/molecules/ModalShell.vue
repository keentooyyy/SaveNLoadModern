<template>
  <Teleport to="body">
    <div
      v-if="open"
      ref="modalEl"
      class="modal fade modal-shell-root"
      :class="[modalClass, { show: showState, 'd-block': open }]"
      tabindex="-1"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="labelledBy"
      :style="{ display: open ? 'block' : 'none' }"
      @click.self="$emit('backdrop')"
    >
      <div class="modal-dialog modal-dialog-centered" :class="dialogClass" :style="dialogStyle">
        <div class="modal-content modal-shell">
          <slot name="header" />
          <slot name="body" />
          <slot name="footer" />
        </div>
      </div>
    </div>
    <div
      v-if="open"
      class="modal-backdrop fade modal-shell-backdrop"
      :class="[backdropClass, { show: showState }]"
    ></div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, watch, ref } from 'vue';

const getModalStack = () => {
  const root = window as typeof window & { __snl_modal_stack?: string[] };
  if (!root.__snl_modal_stack) {
    root.__snl_modal_stack = [];
  }
  return root.__snl_modal_stack;
};

const props = defineProps({
  open: { type: Boolean, default: false },
  show: { type: Boolean, default: undefined },
  labelledBy: { type: String, default: '' },
  modalClass: { type: String, default: '' },
  backdropClass: { type: String, default: '' },
  dialogClass: { type: String, default: '' },
  dialogStyle: { type: [String, Object], default: '' }
});

const emit = defineEmits(['backdrop']);

const modalEl = ref<HTMLElement | null>(null);
const modalId = `modal_${Math.random().toString(36).slice(2, 9)}`;

const showState = computed(() => (props.show === undefined ? props.open : props.show));

const addToStack = () => {
  const stack = getModalStack();
  if (!stack.includes(modalId)) {
    stack.push(modalId);
  }
};

const removeFromStack = () => {
  const stack = getModalStack();
  const index = stack.indexOf(modalId);
  if (index !== -1) {
    stack.splice(index, 1);
  }
};

const isTopmost = () => {
  const stack = getModalStack();
  return stack[stack.length - 1] === modalId;
};

const handleKeydown = (event: KeyboardEvent) => {
  if (event.key !== 'Escape') {
    return;
  }
  if (!isTopmost()) {
    return;
  }
  event.stopPropagation();
  emit('backdrop');
};

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      addToStack();
      window.addEventListener('keydown', handleKeydown);
    } else {
      removeFromStack();
      window.removeEventListener('keydown', handleKeydown);
    }
  },
  { immediate: true }
);

onBeforeUnmount(() => {
  removeFromStack();
  window.removeEventListener('keydown', handleKeydown);
});

defineExpose({ modalEl });
</script>

<style scoped>
.modal-shell-root {
  position: fixed;
  inset: 0;
  overflow-y: auto;
  outline: 0;
}

.modal-shell-backdrop {
  position: fixed;
  inset: 0;
  background: var(--overlay-bg, rgba(0, 0, 0, 0.6));
}
</style>
