<template>
  <BaseCard>
    <SectionHeader title="Operation queue" subtitle="Admin monitoring" />
    <div class="row text-center mt-3">
      <div class="col-4">
        <div class="text-secondary small">Pending</div>
        <div class="h4 mb-0">6</div>
      </div>
      <div class="col-4">
        <div class="text-secondary small">Active</div>
        <div class="h4 mb-0">2</div>
      </div>
      <div class="col-4">
        <div class="text-secondary small">Completed</div>
        <div class="h4 mb-0">18</div>
      </div>
    </div>
    <div class="mt-3">
      <BaseButton size="sm" variant="secondary">Purge queue</BaseButton>
    </div>
  </BaseCard>
</template>

<script setup lang="ts">
import BaseButton from '@/components/atoms/BaseButton.vue';
import BaseCard from '@/components/atoms/BaseCard.vue';
import SectionHeader from '@/components/molecules/SectionHeader.vue';
</script>
