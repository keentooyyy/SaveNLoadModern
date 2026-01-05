<template>
  <div class="card" :class="cardClass">
    <div class="card-body" :class="bodyClass">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps({
  cardClass: { type: String, default: 'bg-dark text-white shadow-sm' },
  bodyClass: { type: String, default: '' }
});
</script>
