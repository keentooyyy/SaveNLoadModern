<template>
  <div class="modal fade" id="gameSearchModal" tabindex="-1" aria-labelledby="gameSearchModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-scrollable modal-dialog-centered modal-lg" style="max-width: 900px;">
      <div class="modal-content modal-shell">
        <div class="modal-header modal-shell__header">
          <h5 class="modal-title text-white" id="gameSearchModalLabel">Select Item</h5>
          <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body modal-shell__body overflow-auto" style="max-height: 500px;">
          <LoadingState v-if="loading" message="Searching..." spinner-class="text-secondary" />
          <EmptyState v-else-if="error" :message="error" />
          <EmptyState v-else-if="!results.length" message="No games found." />
          <div v-else class="search-results">
            <div
              v-for="game in results"
              :key="game.id"
              class="bg-primary text-white d-flex align-items-center gap-3 result-item"
              role="button"
              tabindex="0"
              @click="emit('select', game)"
              @keydown.enter.prevent="emit('select', game)"
            >
              <div v-if="game.banner" class="flex-shrink-0 rounded overflow-hidden bg-dark thumb">
                <img :src="game.banner" :alt="game.name" class="w-100 h-100 object-fit-cover" referrerpolicy="no-referrer" />
              </div>
              <div v-else class="flex-shrink-0 rounded bg-dark d-flex align-items-center justify-content-center thumb">
                <i class="fas fa-gamepad text-white-50 fs-4"></i>
              </div>
              <div class="flex-grow-1 min-w-0">
                <div class="fw-semibold text-truncate">
                  {{ formatTitle(game) }}
                </div>
                <div class="text-white-50 small text-truncate">{{ formatSubtitle(game) }}</div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer modal-shell__footer d-flex gap-2">
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
import LoadingState from '@/components/molecules/LoadingState.vue';
import EmptyState from '@/components/molecules/EmptyState.vue';

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

const formatSubtitle = (game: any) => {
  const genres = game?.genres;
  if (Array.isArray(genres) && genres.length) {
    return genres.join(', ');
  }
  if (typeof genres === 'string' && genres.trim()) {
    return genres;
  }
  return game?.company || '';
};
</script>

<style scoped>
.result-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  transition: background-color 0.15s ease;
  padding: 0.75rem 1rem;
}

.result-item:hover,
.result-item:focus-visible {
  background-color: var(--primary-opacity-20) !important;
  border-color: var(--white-opacity-20);
  outline: none;
}

.result-item .thumb {
  width: 60px;
  height: 60px;
}

.search-results {
  border-radius: 0;
}
</style>
