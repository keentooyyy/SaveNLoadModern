<template>
  <BaseCard>
    <SectionHeader title="Operation queue" subtitle="Admin monitoring" />
    <div class="row text-center mt-3">
      <div class="col-4">
        <StatBadge label="Pending" :value="6" />
      </div>
      <div class="col-4">
        <StatBadge label="Active" :value="2" />
      </div>
      <div class="col-4">
        <StatBadge label="Completed" :value="18" />
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
import StatBadge from '@/components/molecules/StatBadge.vue';
</script>
