<template>
  <Teleport to="body">
    <div v-if="open" class="modal fade show backup-complete-modal" tabindex="-1" role="dialog" aria-modal="true" :aria-labelledby="titleId">
      <div class="modal-dialog modal-dialog-centered" style="max-width: 520px;">
        <div class="modal-content bg-primary text-white border-0 rounded-3 shadow-lg border border-secondary">
          <div class="modal-header bg-primary border-secondary px-4 py-3">
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

          <div class="modal-body bg-primary px-4 py-3">
            <p class="text-white mb-3">Your backup has been saved successfully.</p>
            <div class="card bg-dark border-secondary mb-3">
              <div class="card-body py-2">
                <small class="text-white-50 d-block mb-1">File Location</small>
                <code class="text-info d-block backup-modal-path">{{ zipPath }}</code>
              </div>
            </div>
          </div>

          <div class="modal-footer bg-primary border-secondary d-flex justify-content-end px-4 py-3">
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
        </div>
      </div>
    </div>
    <div v-if="open" class="modal-backdrop fade show backup-complete-backdrop"></div>
  </Teleport>
</template>

<script setup lang="ts">
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
