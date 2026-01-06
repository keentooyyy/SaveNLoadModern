<template>
  <div id="availableGamesSection" class="container-fluid px-3 px-md-4 pt-4 pb-5">
    <div class="d-flex justify-content-between align-items-center mb-4 flex-column flex-md-row gap-3">
      <div class="d-flex justify-content-between align-items-center w-100 w-md-auto">
        <h4 class="text-white mb-0 fw-bold">Available games</h4>
        <button
          class="btn btn-primary d-md-none"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#gameSearchSortCollapse"
          aria-expanded="false"
          aria-controls="gameSearchSortCollapse"
        >
          <i class="fas fa-filter"></i> Filter
        </button>
      </div>
      <div id="gameSearchSortCollapse" class="collapse d-md-flex gap-2 align-items-center w-100 w-md-auto py-2 py-md-0">
        <div class="d-flex flex-column flex-md-row gap-2 w-100 w-md-auto">
          <div class="position-relative flex-grow-1">
            <TextInput v-model="searchQuery" placeholder="Search games..." input-class="border-secondary pe-5 w-100" />
            <i
              class="fas fa-search position-absolute top-50 end-0 translate-middle-y me-3 text-white-50 pointer-events-none"
            ></i>
          </div>
          <select v-model="sortBy" class="form-select bg-primary border-secondary text-white flex-shrink-0 w-auto">
            <option value="name_asc">Sort: Name (A-Z)</option>
            <option value="name_desc">Sort: Name (Z-A)</option>
            <option value="last_saved_desc">Sort: Last Saved (Recent)</option>
            <option value="last_saved_asc">Sort: Last Saved (Oldest)</option>
          </select>
        </div>
      </div>
    </div>
    <div id="availableGamesContainer" class="row g-3">
      <div v-if="loading" class="col-12">
        <div class="d-flex justify-content-center py-5">
          <div class="spinner-border text-light" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
        </div>
      </div>
      <div v-else-if="searching" class="col-12">
        <div class="d-flex justify-content-center align-items-center py-4 text-white-50 gap-2">
          <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
          <span>Searching games...</span>
        </div>
      </div>
      <div
        v-else
        v-for="game in games"
        :key="game.id"
        class="col-12 col-sm-6 col-md-4 col-lg-3 col-xxl-2"
      >
        <GameCard
          :title="game.title"
          :footer="game.footer"
          :image="game.image"
          card-height="320px"
          card-padding="1rem"
          title-size="1rem"
          title-margin-bottom="0.25rem"
          footer-size="0.875rem"
          title-tag="h5"
          :show-actions="true"
          :saving="savingId === game.id"
          :loading="loadingId === game.id"
          @click="emit('open', game)"
          @save="emit('save', game)"
          @load="emit('load', game)"
        />
      </div>
      <div v-if="!loading && !games.length" class="col-12">
        <div class="text-center py-5">
          <p class="text-white-50 mb-2">No games available</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue';
import GameCard from '@/components/molecules/GameCard.vue';
import TextInput from '@/components/atoms/TextInput.vue';

defineProps({
  games: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  savingId: { type: Number, default: null },
  loadingId: { type: Number, default: null },
  searching: { type: Boolean, default: false }
});

const emit = defineEmits(['search', 'open', 'save', 'load']);
const searchQuery = defineModel<string>('search', { default: '' });
const sortBy = defineModel<string>('sort', { default: 'name_asc' });

let searchTimer: number | null = null;

watch([searchQuery, sortBy], () => {
  if (searchTimer) {
    window.clearTimeout(searchTimer);
  }
  searchTimer = window.setTimeout(() => {
    emit('search', { query: searchQuery.value, sort: sortBy.value });
  }, 250);
});

onBeforeUnmount(() => {
  if (searchTimer) {
    window.clearTimeout(searchTimer);
  }
});
</script>

<style scoped>
.pointer-events-none {
  pointer-events: none;
}
</style>
