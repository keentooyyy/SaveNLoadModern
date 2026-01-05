<template>
  <div class="modal fade" id="gameSearchModal" tabindex="-1" aria-labelledby="gameSearchModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-scrollable modal-dialog-centered modal-lg modal-search-dialog">
      <div class="modal-content bg-primary text-white border-0">
        <div class="modal-header bg-primary border-secondary">
          <h5 class="modal-title text-white" id="gameSearchModalLabel">Select Item</h5>
          <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body bg-primary modal-search-body overflow-y-auto">
          <div v-if="loading" class="text-center py-4">
            <div class="spinner-border text-secondary" role="status">
              <span class="visually-hidden">Loading...</span>
            </div>
            <p class="text-white-50 mt-2">Searching...</p>
          </div>
          <div v-else-if="error" class="text-center py-4">
            <p class="text-white-50 mb-0">{{ error }}</p>
          </div>
          <div v-else-if="!results.length" class="text-center py-4">
            <p class="text-white-50 mb-0">No games found.</p>
          </div>
          <div v-else class="p-0 m-0">
            <div
              v-for="game in results"
              :key="game.id"
              class="search-list-item"
              @click="emit('select', game)"
            >
              <div v-if="game.banner" class="search-img-container">
                <img :src="game.banner" :alt="game.name" class="w-100 h-100 object-fit-cover" referrerpolicy="no-referrer" />
              </div>
              <div v-else class="search-img-container d-flex align-items-center justify-content-center">
                <i class="fas fa-gamepad text-white-50 fs-4"></i>
              </div>
              <div class="search-text-container">
                <div class="search-title">
                  {{ formatTitle(game) }}
                </div>
                <div class="search-subtitle">{{ game.company || '' }}</div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer bg-primary border-secondary d-flex gap-2">
          <InputGroup
            button-first
            v-model="query"
            placeholder="Type game name to search..."
            button-label="Search"
            button-icon="fa-search"
            button-class="text-white"
            @action="emit('search')"
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

const emit = defineEmits(['search', 'select']);

const query = defineModel<string>('query', { default: '' });

defineProps({
  results: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' }
});

const formatTitle = (game: any) => {
  const title = game?.name || 'Unknown';
  const year = game?.year || '';
  return year ? `${title} (${year})` : title;
};
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
