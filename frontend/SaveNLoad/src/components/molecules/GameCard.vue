<template>
  <div class="card border-0 shadow h-100 game-card">
    <div
      v-if="image"
      class="card-img-wrapper position-relative overflow-hidden bg-body game-card-img-wrapper"
      :style="{ '--card-height': cardHeight }"
    >
      <img :src="image" class="card-img-top w-100 h-100 game-card-img object-fit-cover" :alt="title" />
      <div class="position-absolute bottom-0 start-0 end-0 p-2 game-card-overlay">
        <component :is="titleTag" class="card-title text-white fw-bold mb-0 game-card-title">
          {{ title }}
        </component>
        <small v-if="footer" class="text-white-50 d-flex align-items-center mb-2 game-card-footer-text">
          <i class="fas fa-clock me-1"></i>
          {{ footer }}
        </small>
        <div v-if="showActions" class="d-flex gap-2 mt-2">
          <button class="btn btn-sm btn-success flex-fill">
            <i class="fas fa-upload me-1"></i> Save
          </button>
          <button class="btn btn-sm btn-primary flex-fill">
            <i class="fas fa-download me-1"></i> Quick Load
          </button>
        </div>
      </div>
    </div>
    <div
      v-else
      class="card-body d-flex align-items-center justify-content-center bg-body game-card-body-wrapper"
      :style="{ '--card-height': cardHeight }"
    >
      <div class="text-center w-100">
        <component :is="titleTag" class="card-title text-white mb-2">{{ title }}</component>
        <p v-if="footer" class="text-white-50 mb-3 small">{{ footer }}</p>
        <div v-if="showActions" class="d-flex gap-2 justify-content-center">
          <button class="btn btn-sm btn-success">
            <i class="fas fa-upload me-1"></i> Save
          </button>
          <button class="btn btn-sm btn-primary">
            <i class="fas fa-download me-1"></i> Quick Load
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps({
  title: { type: String, default: '' },
  footer: { type: String, default: '' },
  image: { type: String, default: '' },
  cardHeight: { type: String, default: '180px' },
  titleTag: { type: String, default: 'h6' },
  showActions: { type: Boolean, default: false }
});
</script>

<style scoped>
.game-card {
  cursor: pointer;
  transition: transform 0.3s ease;
}

.game-card:hover {
  transform: translateY(-4px);
}

.game-card-img {
  transition: transform 0.5s ease;
}

.game-card:hover .game-card-img {
  transform: scale(1.1);
}

.game-card-overlay {
  background: linear-gradient(to top, var(--black-opacity-80) 0%, var(--black-opacity-40) 50%, transparent 100%);
  transition: opacity 0.3s ease;
}

.game-card:hover .game-card-overlay {
  background: linear-gradient(to top, var(--black-opacity-90) 0%, var(--black-opacity-50) 50%, transparent 100%);
}

.game-card-img-wrapper {
  height: var(--card-height, 180px);
}

.game-card-body-wrapper {
  min-height: var(--card-height, 180px);
}

.game-card-title {
  font-size: var(--card-title-size, 0.9rem);
}

.game-card-footer-text {
  font-size: var(--card-footer-size, 0.75rem);
}
</style>
