<template>
  <div class="modal fade" id="gameSavesModal" tabindex="-1" aria-labelledby="gameSavesModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered modal-lg">
        <div class="modal-content bg-primary text-white border-0 rounded-3 shadow-lg border border-secondary">
          <div class="modal-header bg-primary border-secondary px-4 py-3">
            <div class="d-flex flex-column gap-1">
              <h5 class="modal-title text-white" id="gameSavesModalLabel">
                Available Saves<span v-if="title"> · {{ title }}</span>
              </h5>
              <small v-if="!loading" class="text-uppercase text-white-50 small">{{ saveFolders.length }} saved</small>
            </div>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body bg-primary overflow-auto px-4 py-3" style="max-height: 70vh;">
          <SaveActionsBar
            :loading="loading"
            :has-saves="!!saveFolders.length"
            @open-location="emit('open-location')"
            @backup-all="emit('backup-all')"
            @delete-all="emit('delete-all')"
          />

          <div v-if="loading" class="text-center py-4">
            <div class="spinner-border text-secondary" role="status">
              <span class="visually-hidden">Loading...</span>
            </div>
            <p class="text-white-50 mt-2">Loading saves...</p>
          </div>

          <div v-else-if="error" class="text-center py-4">
            <p class="text-white-50 mb-0">{{ error }}</p>
          </div>

          <div v-else-if="!saveFolders.length" class="text-center py-4">
            <p class="text-white-50 mb-0">No saves available</p>
          </div>

          <div v-else class="d-grid gap-2">
            <SaveFolderItem
              v-for="folder in saveFolders"
              :key="folder.folder_number"
              :folder="folder"
              @load="emit('load', folder)"
              @delete="emit('delete', folder)"
            />
          </div>
        </div>
        <div
          class="modal-footer bg-primary border-secondary d-flex align-items-center px-4 py-3"
          :class="isAdmin ? 'justify-content-between' : 'justify-content-end'"
        >
          <div v-if="isAdmin" class="d-flex gap-2 modal-footer-admin">
            <button type="button" class="btn btn-outline-secondary text-white modal-footer-btn" @click="emit('edit-game')">
              <i class="fas fa-edit me-1"></i>
              Edit
            </button>
            <button type="button" class="btn btn-outline-danger text-white modal-footer-btn" @click="emit('delete-game')">
              <i class="fas fa-trash me-1"></i>
              Delete
            </button>
          </div>
          <button type="button" class="btn btn-outline-secondary text-white modal-footer-btn" data-bs-dismiss="modal">
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import SaveActionsBar from '@/components/molecules/SaveActionsBar.vue';
import SaveFolderItem from '@/components/molecules/SaveFolderItem.vue';
type SaveFolder = {
  folder_number: number;
  created_at: string;
};

defineProps({
  title: { type: String, default: '' },
  saveFolders: { type: Array as () => SaveFolder[], default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  isAdmin: { type: Boolean, default: false }
});

const emit = defineEmits(['load', 'delete', 'backup-all', 'delete-all', 'open-location', 'edit-game', 'delete-game']);

</script>

<style scoped>
.modal-footer-btn {
  min-width: 104px;
}

@media (max-width: 575.98px) {
  .modal-footer {
    flex-direction: column;
    align-items: stretch;
    gap: 0.75rem;
  }

  .modal-footer-admin {
    flex-direction: column;
  }

  .modal-footer > div,
  .modal-footer-btn {
    width: 100%;
  }
}
</style>
