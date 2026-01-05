<template>
  <div class="container-fluid px-4 pt-3 pb-2 position-relative">
    <div class="d-flex align-items-center justify-content-between mb-2">
      <h6 class="text-white mb-0 fs-6 fw-medium">Recently played games</h6>
      <div class="d-flex gap-2">
        <button class="btn btn-outline-light btn-sm" type="button" aria-label="Scroll left">
          <i class="fas fa-chevron-left"></i>
        </button>
        <button class="btn btn-outline-light btn-sm" type="button" aria-label="Scroll right">
          <i class="fas fa-chevron-right"></i>
        </button>
      </div>
    </div>
    <div class="d-flex gap-2 overflow-x-auto pb-2 cards-scroll-container scrollbar-thin">
      <div v-if="loading" class="d-flex justify-content-center align-items-center w-100 py-3">
        <div class="spinner-border text-light" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>
      <div v-else-if="items.length" class="d-flex gap-2">
        <div v-for="item in items" :key="item.id" class="flex-shrink-0 recent-game-card recent-game-card-width">
          <GameCard :title="item.title" :footer="item.footer" :image="item.image" @click="emit('select', item)" />
        </div>
      </div>
      <div v-else class="flex-shrink-0 w-100">
        <div class="text-center py-3">
          <p class="text-white-50 mb-0">No recently played games</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import GameCard from '@/components/molecules/GameCard.vue';

const emit = defineEmits(['select']);

defineProps({
  items: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
});
</script>

<style scoped>
.recent-game-card {
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.recent-game-card:hover {
  transform: translateY(-2px);
}

.recent-game-card:hover :deep(.card) {
  box-shadow: 0 4px 12px var(--black-opacity-30) !important;
}

.recent-game-card-width {
  width: 260px;
}

.overflow-x-auto::-webkit-scrollbar {
  height: 8px;
}

.overflow-x-auto::-webkit-scrollbar-track {
  background: var(--white-opacity-10);
  border-radius: 4px;
}

.overflow-x-auto::-webkit-scrollbar-thumb {
  background: var(--white-opacity-30);
  border-radius: 4px;
}

.overflow-x-auto::-webkit-scrollbar-thumb:hover {
  background: var(--white-opacity-50);
}

.scrollbar-thin {
  scrollbar-width: thin;
}
</style>
