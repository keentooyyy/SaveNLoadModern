<template>
  <div class="container-fluid px-4 pt-3 pb-2 position-relative">
    <div class="d-flex align-items-center justify-content-between mb-2">
      <h6 class="text-white mb-0 fs-6 fw-medium">Recently played games</h6>
      <div class="d-flex gap-2">
        <button
          class="btn btn-outline-light btn-sm"
          type="button"
          aria-label="Scroll left"
          :disabled="!canScrollLeft"
          @click="scrollLeft"
        >
          <i class="fas fa-chevron-left"></i>
        </button>
        <button
          class="btn btn-outline-light btn-sm"
          type="button"
          aria-label="Scroll right"
          :disabled="!canScrollRight"
          @click="scrollRight"
        >
          <i class="fas fa-chevron-right"></i>
        </button>
      </div>
    </div>
    <div
      ref="scrollContainer"
      class="d-flex gap-2 overflow-x-auto pb-2 cards-scroll-container scrollbar-thin"
      @scroll="updateScrollState"
      @wheel="handleWheel"
    >
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
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';
import GameCard from '@/components/molecules/GameCard.vue';

const emit = defineEmits(['select']);

const props = defineProps({
  items: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
});

const scrollContainer = ref<HTMLElement | null>(null);
const canScrollLeft = ref(false);
const canScrollRight = ref(false);

const updateScrollState = () => {
  const el = scrollContainer.value;
  if (!el) {
    canScrollLeft.value = false;
    canScrollRight.value = false;
    return;
  }

  const maxScrollLeft = el.scrollWidth - el.clientWidth;
  canScrollLeft.value = el.scrollLeft > 1;
  canScrollRight.value = maxScrollLeft - el.scrollLeft > 1;
};

const scrollByAmount = (direction: -1 | 1) => {
  const el = scrollContainer.value;
  if (!el) {
    return;
  }
  const amount = Math.max(200, Math.floor(el.clientWidth * 0.8));
  el.scrollBy({ left: amount * direction, behavior: 'smooth' });
};

const scrollLeft = () => scrollByAmount(-1);
const scrollRight = () => scrollByAmount(1);

const handleWheel = (event: WheelEvent) => {
  const el = scrollContainer.value;
  if (!el) {
    return;
  }

  const maxScrollLeft = el.scrollWidth - el.clientWidth;
  if (maxScrollLeft <= 0) {
    return;
  }

  if (Math.abs(event.deltaY) <= Math.abs(event.deltaX)) {
    return;
  }

  event.preventDefault();
  el.scrollLeft += event.deltaY;
};

const handleResize = () => {
  updateScrollState();
};

onMounted(() => {
  updateScrollState();
  window.addEventListener('resize', handleResize);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize);
});

watch(
  () => [props.items.length, props.loading],
  () => {
    requestAnimationFrame(() => updateScrollState());
  }
);
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
