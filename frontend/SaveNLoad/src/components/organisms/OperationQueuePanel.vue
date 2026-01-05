<template>
  <CollapsibleCard
    title="Operation Queue Management"
    icon="fa-tasks"
    collapse-id="operationQueueCollapse"
    header-class="operation-queue-header"
    icon-class="operation-queue-icon"
    title-class="operation-queue-title"
    chevron-class="operation-queue-chevron"
    chevron-id="operationQueueChevron"
  >
    <div class="mb-4">
      <SectionTitle text="Queue Statistics" />
      <div id="operationQueueStats" class="text-white">
        <div class="text-center py-3">
          <div class="spinner-border text-light" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
        </div>
      </div>
    </div>

    <hr class="border-secondary my-4" />

    <div>
      <SectionTitle text="Clear Operations" />
      <IconButton type="button" variant="secondary" class="text-white fw-bold" icon="fa-trash" id="clearOperationsBtn">
        Clear All Operations
      </IconButton>
    </div>
  </CollapsibleCard>
</template>

<script setup lang="ts">
import CollapsibleCard from '@/components/molecules/CollapsibleCard.vue';
import IconButton from '@/components/atoms/IconButton.vue';
import SectionTitle from '@/components/atoms/SectionTitle.vue';
</script>
