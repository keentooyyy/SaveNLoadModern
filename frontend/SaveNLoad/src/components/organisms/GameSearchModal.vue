<template>
  <div class="modal fade" id="gameSearchModal" tabindex="-1" aria-labelledby="gameSearchModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-scrollable modal-dialog-centered modal-lg modal-search-dialog">
      <div class="modal-content bg-primary text-white border-0">
        <div class="modal-header bg-primary border-secondary">
          <h5 class="modal-title text-white" id="gameSearchModalLabel">Select Item</h5>
          <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body bg-primary modal-search-body overflow-y-auto" id="modal_search_results"></div>
        <div class="modal-footer bg-primary border-secondary d-flex gap-2">
          <InputGroup
            button-first
            input-id="modal_search_input"
            placeholder="Type game name to search..."
            button-label="Search"
            button-icon="fa-search"
            button-class="text-white"
            button-id="modal_search_btn"
            class="flex-fill"
          />
          <IconButton type="button" variant="outline-secondary" class="text-white" data-bs-dismiss="modal">
            Cancel
          </IconButton>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import IconButton from '@/components/atoms/IconButton.vue';
import InputGroup from '@/components/molecules/InputGroup.vue';
</script>

<style scoped>
.modal-search-dialog {
  max-width: 900px;
}

.modal-search-body {
  max-height: 500px;
}

.search-list-item {
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  cursor: pointer;
  transition: background-color 0.2s ease;
  border-bottom: 1px solid var(--white-opacity-08);
}

.search-list-item:hover {
  background-color: var(--primary-opacity-15);
}

.search-img-container {
  flex-shrink: 0;
  width: 60px;
  height: 60px;
  margin-right: 1rem;
  border-radius: 4px;
  overflow: hidden;
  background-color: var(--white-opacity-10);
}

.search-text-container {
  flex: 1;
  min-width: 0;
}

.search-title {
  color: var(--color-white);
  font-size: 1rem;
  font-weight: 500;
  margin-bottom: 0.25rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.search-subtitle {
  color: var(--white-opacity-50);
  font-size: 0.875rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
