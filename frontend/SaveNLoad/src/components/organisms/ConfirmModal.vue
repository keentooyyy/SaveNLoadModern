<template>
  <ModalShell
    :open="state.open"
    :show="state.open"
    :labelled-by="titleId"
    modal-class="confirm-modal"
    backdrop-class="confirm-modal-backdrop"
    dialog-style="max-width: 420px;"
    @backdrop="cancelAction"
  >
    <template #header>
      <div class="modal-header modal-shell__header">
        <h5 :id="titleId" class="modal-title text-white mb-0">{{ state.title }}</h5>
        <button class="btn-close btn-close-white" type="button" aria-label="Close" @click="cancelAction"></button>
      </div>
    </template>
    <template #body>
      <div class="modal-body modal-shell__body">
        <p class="text-white-50 mb-0">{{ state.message }}</p>
      </div>
    </template>
    <template #footer>
      <div class="modal-footer modal-shell__footer d-flex justify-content-end">
        <button class="btn btn-outline-secondary text-white" type="button" @click="cancelAction">
          {{ state.cancelText }}
        </button>
        <button :class="confirmButtonClass" type="button" @click="confirmAction">
          {{ state.confirmText }}
        </button>
      </div>
    </template>
  </ModalShell>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useConfirm } from '@/composables/useConfirm';
import ModalShell from '@/components/molecules/ModalShell.vue';

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
