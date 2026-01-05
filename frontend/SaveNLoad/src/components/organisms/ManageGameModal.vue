<template>
  <div class="modal fade" id="gameManageModal" tabindex="-1" aria-labelledby="gameManageModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered modal-lg">
      <div class="modal-content bg-primary text-white border-0">
        <div class="modal-header bg-primary border-0 d-flex align-items-center">
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
        <div class="modal-body bg-primary" style="max-height: 70vh; overflow-y: auto;">
          <div class="tab-content">
            <div class="tab-pane fade show active" id="edit-pane" role="tabpanel">
              <form id="gameManageForm">
                <input type="hidden" id="manage_game_id" name="game_id" />
                <GameFormFields prefix="manage" />
              </form>
            </div>
            <div class="tab-pane fade" id="saves-pane" role="tabpanel">
              <div id="savesListContainer">
                <div class="text-center py-4">
                  <div class="spinner-border text-secondary" role="status">
                    <span class="visually-hidden">Loading...</span>
                  </div>
                  <p class="text-white-50 mt-2">Loading saves...</p>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer bg-primary border-secondary d-flex justify-content-end">
          <FormActions align-class="me-auto" id="edit-tab-buttons">
            <IconButton type="button" variant="outline-danger" class="text-white" icon="fa-trash-alt" id="deleteGameBtn">
              Delete
            </IconButton>
            <IconButton type="button" variant="secondary" class="text-white" id="saveGameBtn">
              Save changes
            </IconButton>
          </FormActions>
          <IconButton type="button" variant="outline-secondary" class="text-white" data-bs-dismiss="modal">
            Close
          </IconButton>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import GameFormFields from '@/components/molecules/GameFormFields.vue';
import FormActions from '@/components/molecules/FormActions.vue';
import IconButton from '@/components/atoms/IconButton.vue';
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
