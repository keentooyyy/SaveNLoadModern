<template>
  <ModalShell
    :open="open"
    :show="open"
    :labelled-by="labelId"
    dialog-class="modal-lg"
  >
    <template #header>
      <div class="modal-header modal-shell__header d-flex align-items-center">
        <ul class="nav nav-tabs border-0 mb-0" role="tablist">
          <li class="nav-item" role="presentation">
            <button
              class="nav-link active text-white d-flex align-items-center"
              id="edit-tab"
              data-bs-toggle="tab"
              data-bs-target="#edit-pane"
              type="button"
              role="tab"
            >
              <i class="fas fa-edit me-2"></i>
              <span>Edit</span>
            </button>
          </li>
          <li class="nav-item" role="presentation" id="saves-tab-container">
            <button
              class="nav-link text-white-50 d-flex align-items-center"
              id="saves-tab"
              data-bs-toggle="tab"
              data-bs-target="#saves-pane"
              type="button"
              role="tab"
            >
              <i class="fas fa-folder me-2"></i>
              <span>Available Saves</span>
            </button>
          </li>
        </ul>
      </div>
    </template>
    <template #body>
      <div class="modal-body modal-shell__body" style="max-height: 70vh; overflow-y: auto;">
        <div class="tab-content">
          <div class="tab-pane fade show active" id="edit-pane" role="tabpanel">
            <form id="gameManageForm">
              <input type="hidden" id="manage_game_id" name="game_id" />
              <GameFormFields prefix="manage" />
            </form>
          </div>
          <div class="tab-pane fade" id="saves-pane" role="tabpanel">
            <div id="savesListContainer">
              <LoadingState message="Loading saves..." spinner-class="text-secondary" />
            </div>
          </div>
        </div>
      </div>
    </template>
    <template #footer>
      <div class="modal-footer modal-shell__footer d-flex justify-content-end">
        <FormActions align-class="me-auto" id="edit-tab-buttons">
          <IconButton type="button" variant="outline-danger" class="text-white" icon="fa-trash-alt" id="deleteGameBtn">
            Delete
          </IconButton>
          <IconButton type="button" variant="secondary" class="text-white" id="saveGameBtn">
            Save changes
          </IconButton>
        </FormActions>
        <IconButton type="button" variant="outline-secondary" class="text-white" @click="emit('close')">
          Close
        </IconButton>
      </div>
    </template>
  </ModalShell>
</template>

<script setup lang="ts">
import ModalShell from '@/components/molecules/ModalShell.vue';
import GameFormFields from '@/components/molecules/GameFormFields.vue';
import FormActions from '@/components/molecules/FormActions.vue';
import IconButton from '@/components/atoms/IconButton.vue';
import LoadingState from '@/components/molecules/LoadingState.vue';

defineProps({
  open: { type: Boolean, default: false }
});

const emit = defineEmits(['close']);

const labelId = `gameManageModalLabel_${Math.random().toString(36).slice(2, 8)}`;
</script>

<style scoped>
#gameManageModal :deep(.nav-tabs) {
  border-bottom: 1px solid var(--white-opacity-10);
}

#gameManageModal :deep(.nav-tabs .nav-link) {
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--white-opacity-50) !important;
  transition: all 0.2s ease;
  background-color: transparent;
}

#gameManageModal :deep(.nav-tabs .nav-link.active) {
  color: var(--color-white) !important;
  background-color: var(--primary-opacity-30) !important;
  border-color: var(--color-primary) var(--color-primary) transparent !important;
  border-bottom-width: 3px !important;
  font-weight: 600;
}

#gameManageModal :deep(.nav-tabs .nav-link.active i) {
  color: var(--color-primary) !important;
}

#gameManageModal :deep(.nav-tabs .nav-link:not(.active):hover) {
  color: var(--color-white) !important;
  background-color: var(--white-opacity-08);
}
</style>
