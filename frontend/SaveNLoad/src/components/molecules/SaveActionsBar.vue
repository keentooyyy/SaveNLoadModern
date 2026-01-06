<template>
  <div class="row g-2 pb-3 mb-3 align-items-stretch d-lg-none">
    <div class="col-12 col-md-4">
      <button class="btn btn-info text-white btn-sm w-100 text-center saves-action-btn" type="button" @click="emit('open-location')">
        <i class="fas fa-folder-open me-2"></i>
        <span class="saves-action-label">Open Save Location</span>
      </button>
    </div>
    <div v-if="showBatchActions" class="col-12 col-md-4">
      <button
        class="btn btn-secondary text-white btn-sm w-100 text-center saves-action-btn"
        type="button"
        @click="emit('backup-all')"
      >
        <i class="fas fa-download me-2"></i>
        <span class="saves-action-label">Backup All Saves</span>
      </button>
    </div>
    <div v-if="showBatchActions" class="col-12 col-md-4">
      <button
        class="btn btn-danger text-white btn-sm w-100 text-center saves-action-btn"
        type="button"
        @click="emit('delete-all')"
      >
        <i class="fas fa-trash me-2"></i>
        <span class="saves-action-label">Delete Older Saves</span>
      </button>
    </div>
  </div>
  <div class="d-none d-lg-flex align-items-stretch justify-content-between gap-2 pb-3 mb-3">
    <div class="flex-grow-0 saves-actions-left">
      <button class="btn btn-info text-white btn-sm text-center saves-action-btn" type="button" @click="emit('open-location')">
        <i class="fas fa-folder-open me-2"></i>
        <span class="saves-action-label">Open Save Location</span>
      </button>
    </div>
    <div v-if="showBatchActions" class="d-flex gap-2 align-items-stretch saves-actions-right">
      <button
        class="btn btn-secondary text-white btn-sm text-center saves-action-btn"
        type="button"
        @click="emit('backup-all')"
      >
        <i class="fas fa-download me-2"></i>
        <span class="saves-action-label">Backup All Saves</span>
      </button>
      <button
        class="btn btn-danger text-white btn-sm text-center saves-action-btn"
        type="button"
        @click="emit('delete-all')"
      >
        <i class="fas fa-trash me-2"></i>
        <span class="saves-action-label">Delete Older Saves</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps({
  loading: { type: Boolean, default: false },
  hasSaves: { type: Boolean, default: false }
});

const emit = defineEmits(['open-location', 'backup-all', 'delete-all']);

const showBatchActions = computed(() => !props.loading && props.hasSaves);
</script>

<style scoped>
.saves-action-btn {
  padding: 0.35rem 0.85rem;
  line-height: 1.15;
}

@media (min-width: 992px) {
  .saves-actions-left,
  .saves-actions-right {
    flex: 0 0 auto;
  }
}
</style>
