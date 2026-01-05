<template>
  <BaseCard>
    <h5 class="mb-1">{{ title }}</h5>
    <p class="text-secondary">{{ subtitle }}</p>
    <slot />
    <div class="d-flex justify-content-end gap-2 mt-3">
      <BaseButton size="sm" variant="secondary">Cancel</BaseButton>
      <BaseButton size="sm">Confirm</BaseButton>
    </div>
  </BaseCard>
</template>

<script setup lang="ts">
import BaseButton from '@/components/atoms/BaseButton.vue';
import BaseCard from '@/components/atoms/BaseCard.vue';

defineProps({
  title: String,
  subtitle: String
});
</script>
