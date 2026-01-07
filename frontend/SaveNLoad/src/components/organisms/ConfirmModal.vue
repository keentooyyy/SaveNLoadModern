<template>
  <Teleport to="body">
    <div
      v-if="state.open"
      class="modal fade show confirm-modal"
      tabindex="-1"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="titleId"
      @click.self="cancelAction"
    >
      <div class="modal-dialog modal-dialog-centered" style="max-width: 420px;">
        <div class="modal-content modal-shell">
          <div class="modal-header modal-shell__header">
            <h5 :id="titleId" class="modal-title text-white mb-0">{{ state.title }}</h5>
            <button class="btn-close btn-close-white" type="button" aria-label="Close" @click="cancelAction"></button>
          </div>
          <div class="modal-body modal-shell__body">
            <p class="text-white-50 mb-0">{{ state.message }}</p>
          </div>
          <div class="modal-footer modal-shell__footer d-flex justify-content-end">
            <button class="btn btn-outline-secondary text-white" type="button" @click="cancelAction">
              {{ state.cancelText }}
            </button>
            <button :class="confirmButtonClass" type="button" @click="confirmAction">
              {{ state.confirmText }}
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="state.open" class="modal-backdrop fade show confirm-modal-backdrop"></div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useConfirm } from '@/composables/useConfirm';

const { state, confirmAction, cancelAction } = useConfirm();
const titleId = `confirmModalTitle_${Math.random().toString(36).slice(2, 8)}`;

const confirmButtonClass = computed(() => {
  return state.variant === 'danger'
    ? 'btn btn-danger text-white'
    : 'btn btn-light text-primary';
});
</script>

<style scoped>
.confirm-modal {
  display: block;
  z-index: 1250;
}

.confirm-modal-backdrop {
  background: var(--overlay-bg);
  z-index: 1240;
}
</style>
