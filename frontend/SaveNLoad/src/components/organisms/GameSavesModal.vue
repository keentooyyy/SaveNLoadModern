<template>
  <div class="modal fade" id="gameSavesModal" tabindex="-1" aria-labelledby="gameSavesModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered modal-lg">
      <div class="modal-content bg-primary text-white border-0">
        <div class="modal-header bg-primary border-secondary">
          <h5 class="modal-title text-white" id="gameSavesModalLabel">
            Available Saves<span v-if="title"> - {{ title }}</span>
          </h5>
          <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body bg-primary" style="max-height: 70vh; overflow-y: auto;">
          <div class="text-center py-4">
            <div class="spinner-border text-secondary" role="status">
              <span class="visually-hidden">Loading...</span>
            </div>
            <p class="text-white-50 mt-2">Loading saves...</p>
          </div>
        </div>
        <div class="modal-footer bg-primary border-secondary d-flex justify-content-end">
          <button type="button" class="btn btn-outline-secondary text-white" data-bs-dismiss="modal">
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps({
  title: { type: String, default: '' }
});
</script>
