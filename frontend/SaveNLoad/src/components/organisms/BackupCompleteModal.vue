<template>
  <ModalShell
    :open="open"
    :show="open"
    :labelled-by="titleId"
    modal-class="backup-complete-modal"
    backdrop-class="backup-complete-backdrop"
    dialog-style="max-width: 520px;"
  >
    <template #header>
      <div class="modal-header modal-shell__header">
        <div class="d-flex flex-column gap-1">
          <h5 :id="titleId" class="modal-title text-white mb-0">Backup Complete</h5>
        </div>
        <button
          class="btn-close btn-close-white"
          type="button"
          aria-label="Close"
          @click="onClose"
        ></button>
      </div>
    </template>
    <template #body>
      <div class="modal-body modal-shell__body">
        <p class="text-white mb-3">Your backup has been saved successfully.</p>
        <div class="card bg-dark border-secondary mb-3">
          <div class="card-body py-2">
            <small class="text-white-50 d-block mb-1">File Location</small>
            <code class="text-info d-block backup-modal-path">{{ zipPath }}</code>
          </div>
        </div>
      </div>
    </template>
    <template #footer>
      <div class="modal-footer modal-shell__footer d-flex justify-content-end">
        <button class="btn btn-outline-secondary text-white" type="button" @click="onClose">Close</button>
        <button
          v-if="zipPath"
          class="btn btn-light text-primary"
          type="button"
          @click="onOpenLocation"
        >
          Open Folder
        </button>
      </div>
    </template>
  </ModalShell>
</template>

<script setup lang="ts">
import ModalShell from '@/components/molecules/ModalShell.vue';

const props = defineProps({
  open: { type: Boolean, default: false },
  zipPath: { type: String, default: '' }
});

const emit = defineEmits(['close', 'open-location']);

const titleId = `backupModalTitle_${Math.random().toString(36).slice(2, 8)}`;

const onClose = () => {
  emit('close');
};

const onOpenLocation = () => {
  if (!props.zipPath) {
    return;
  }
  emit('open-location');
};
</script>

<style scoped>
.backup-complete-modal {
  display: block;
  z-index: 1250;
}

.backup-complete-backdrop {
  background: var(--overlay-bg);
  z-index: 1240;
}

.backup-modal-path {
  word-break: break-all;
}

</style>
