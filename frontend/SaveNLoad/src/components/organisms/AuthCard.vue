<template>
  <BaseCard card-class="shadow-lg card-primary" body-class="p-3 p-md-4">
    <div class="text-center mb-4">
      <img src="/images/icon.png" alt="Save N Load" width="50" height="50" />
    </div>
    <h2 class="card-title mt-3">{{ title }}</h2>
    <p class="fs-6 opacity-50 text-white mb-4">{{ subtitle }}</p>
    <slot />
  </BaseCard>
</template>

<script setup lang="ts">
import BaseCard from '@/components/atoms/BaseCard.vue';

defineProps({
  title: String,
  subtitle: String
});
</script>
