<template>
  <div class="modal fade" id="gameSavesModal" tabindex="-1" aria-labelledby="gameSavesModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered modal-lg">
        <div class="modal-content bg-primary text-white border-0 saves-modal">
          <div class="modal-header bg-primary border-secondary saves-modal-header">
            <div class="saves-modal-title">
              <h5 class="modal-title text-white" id="gameSavesModalLabel">
                Available Saves<span v-if="title"> · {{ title }}</span>
              </h5>
              <span class="saves-count" v-if="!loading">{{ saveFolders.length }} saved</span>
            </div>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body bg-primary saves-modal-body">
          <div class="saves-actions">
            <button class="btn btn-info text-white btn-sm" type="button" @click="emit('open-location')">
              <i class="fas fa-folder-open me-2"></i>
              <span class="saves-action-label">Open Save Location</span>
            </button>
            <div class="d-flex gap-2">
              <button
                v-if="!loading && saveFolders.length"
                class="btn btn-secondary text-white btn-sm"
                type="button"
                @click="emit('backup-all')"
              >
                <i class="fas fa-download me-2"></i>
                <span class="saves-action-label">Backup All Saves</span>
              </button>
              <button
                v-if="!loading && saveFolders.length"
                class="btn btn-danger text-white btn-sm"
                type="button"
                @click="emit('delete-all')"
              >
                <i class="fas fa-trash me-2"></i>
                <span class="saves-action-label">Delete All Saves</span>
              </button>
            </div>
          </div>

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

          <div v-else class="list-group saves-list">
            <div
              v-for="folder in saveFolders"
              :key="folder.folder_number"
              class="list-group-item bg-primary text-white border-secondary transition-bg list-group-item-hover saves-item"
            >
              <div class="d-flex justify-content-between align-items-center">
                <div class="saves-item-main">
                  <h6 class="mb-1 text-white">Save {{ folder.folder_number }}</h6>
                  <small class="text-white-50">{{ formatDate(folder.created_at) }}</small>
                </div>
                <div class="d-flex gap-2">
                  <button class="btn btn-sm btn-secondary text-white" type="button" @click="emit('load', folder)">
                    <i class="fas fa-download me-1"></i>
                    Load
                  </button>
                  <button class="btn btn-sm btn-outline-danger text-white" type="button" @click="emit('delete', folder)">
                    <i class="fas fa-trash me-1"></i>
                    Delete
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer bg-primary border-secondary d-flex justify-content-end saves-modal-footer">
          <button type="button" class="btn btn-outline-secondary text-white" data-bs-dismiss="modal">
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
type SaveFolder = {
  folder_number: number;
  created_at: string;
};

defineProps({
  title: { type: String, default: '' },
  saveFolders: { type: Array as () => SaveFolder[], default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' }
});

const emit = defineEmits(['load', 'delete', 'backup-all', 'delete-all', 'open-location']);

const formatDate = (value: string) => {
  if (!value) {
    return '';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  const datePart = date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });
  const timePart = date
    .toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
  return `${datePart} ${timePart}`;
};
</script>

<style scoped>
.saves-modal {
  border-radius: 14px;
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.45);
  border: 1px solid var(--white-opacity-08);
  overflow: hidden;
}

.saves-modal-header {
  border-bottom: 1px solid var(--white-opacity-10);
  padding: 1.1rem 1.4rem;
}

.saves-modal-title {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.saves-count {
  font-size: 0.8rem;
  color: var(--white-opacity-50);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.saves-modal-body {
  max-height: 70vh;
  overflow-y: auto;
  padding: 1.25rem 1.4rem 1.4rem;
}

.saves-actions {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  padding-bottom: 0.75rem;
  margin-bottom: 1rem;
}

.saves-list {
  display: grid;
  gap: 0.65rem;
}

.saves-item {
  border-radius: 10px;
  border: 1px solid var(--white-opacity-10);
  background: var(--white-opacity-08);
  padding: 0.9rem 1rem;
}

.saves-modal-footer {
  border-top: 1px solid var(--white-opacity-10);
  padding: 0.9rem 1.4rem 1.2rem;
}

@media (max-width: 767.98px) {
  .saves-actions {
    flex-direction: row;
    align-items: center;
    flex-wrap: wrap;
  }

  .saves-modal-body {
    padding: 1rem;
  }

  .saves-action-label {
    display: none;
  }

  .saves-actions .btn {
    padding: 0.35rem 0.55rem;
  }

  .saves-actions .btn i {
    margin-right: 0 !important;
  }
}
</style>
