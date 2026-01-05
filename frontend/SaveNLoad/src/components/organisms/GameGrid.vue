<template>
  <div id="availableGamesSection" class="container-fluid px-4 pt-4 pb-5">
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
      <div
        id="gameSearchSortCollapse"
        class="collapse d-md-flex gap-2 align-items-center w-100 w-md-auto py-2 py-md-0"
      >
        <div class="d-flex flex-column flex-md-row gap-2 w-100 w-md-auto">
          <div class="position-relative flex-grow-1 search-input-container">
            <input
              type="text"
              class="form-control bg-primary border-secondary text-white pe-5 w-100"
              placeholder="Search games..."
            />
            <i
              class="fas fa-search position-absolute top-50 end-0 translate-middle-y me-3 text-white-50 pointer-events-none"
            ></i>
          </div>
          <select class="form-select bg-primary border-secondary text-white flex-shrink-0 sort-select-width">
            <option value="name_asc">Sort: Name (A-Z)</option>
            <option value="name_desc">Sort: Name (Z-A)</option>
            <option value="last_saved_desc">Sort: Last Saved (Recent)</option>
            <option value="last_saved_asc">Sort: Last Saved (Oldest)</option>
          </select>
        </div>
      </div>
    </div>
    <div id="availableGamesContainer" class="row g-4">
      <div
        v-for="game in games"
        :key="game.id"
        class="col-12 col-sm-6 col-md-4 col-lg-3 col-xxl-2 game-item"
      >
        <GameCard
          :title="game.title"
          :footer="game.footer"
          :image="game.image"
          card-height="320px"
          title-tag="h5"
          :show-actions="true"
        />
      </div>
      <div v-if="!games.length" class="col-12">
        <div class="text-center py-5">
          <p class="text-white-50 mb-2">No games available</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import GameCard from '@/components/molecules/GameCard.vue';

defineProps({
  games: { type: Array, default: () => [] }
});
</script>
