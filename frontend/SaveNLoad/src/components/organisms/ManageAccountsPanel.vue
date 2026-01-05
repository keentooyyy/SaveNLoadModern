<template>
  <CollapsibleCard
    title="Manage Accounts"
    icon="fa-users"
    collapse-id="manageAccountsCollapse"
    header-class="manage-accounts-header"
    icon-class="manage-accounts-icon"
    title-class="manage-accounts-title"
    chevron-class="manage-accounts-chevron"
    chevron-id="manageAccountsChevron"
  >
    <div class="mb-4">
      <InputLabel text="SEARCH BY USERNAME OR EMAIL" label-class="mb-2" />
      <InputGroup
        placeholder="Type username or email to search..."
        button-label="Search"
        button-icon="fa-search"
        button-class="text-white"
      />
    </div>

    <hr class="border-secondary mb-4" />

    <div class="mb-3">
      <SectionTitle text="All Users" />
      <div id="usersList" class="text-white">
        <div class="text-center py-3">
          <div class="spinner-border text-light" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
        </div>
      </div>
    </div>
  </CollapsibleCard>
</template>

<script setup lang="ts">
import CollapsibleCard from '@/components/molecules/CollapsibleCard.vue';
import InputGroup from '@/components/molecules/InputGroup.vue';
import InputLabel from '@/components/atoms/InputLabel.vue';
import SectionTitle from '@/components/atoms/SectionTitle.vue';
</script>
