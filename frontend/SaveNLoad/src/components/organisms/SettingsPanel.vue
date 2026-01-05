<template>
  <BaseCard>
    <SectionHeader title="Account settings" subtitle="Personalize your workspace" />
    <div class="row g-3 mt-3">
      <div class="col-12 col-md-6">
        <FormField label="Display name">
          <BaseInput class="bg-primary border-secondary text-white" placeholder="Player One" />
        </FormField>
      </div>
      <div class="col-12 col-md-6">
        <FormField label="Email">
          <BaseInput class="bg-primary border-secondary text-white" placeholder="you@example.com" />
        </FormField>
      </div>
      <div class="col-12 col-md-6">
        <FormField label="Time zone">
          <BaseInput class="bg-primary border-secondary text-white" placeholder="UTC -05" />
        </FormField>
      </div>
      <div class="col-12 col-md-6">
        <FormField label="Notifications">
          <BaseInput class="bg-primary border-secondary text-white" placeholder="Enabled" />
        </FormField>
      </div>
    </div>
    <div class="d-flex gap-2 mt-3">
      <BaseButton size="sm">Save changes</BaseButton>
      <BaseButton size="sm" variant="secondary">Reset</BaseButton>
    </div>
  </BaseCard>
</template>

<script setup lang="ts">
import BaseButton from '@/components/atoms/BaseButton.vue';
import BaseCard from '@/components/atoms/BaseCard.vue';
import BaseInput from '@/components/atoms/BaseInput.vue';
import FormField from '@/components/molecules/FormField.vue';
import SectionHeader from '@/components/molecules/SectionHeader.vue';
</script>
