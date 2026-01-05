<template>
  <CollapsibleCard
    title="Add Game"
    icon="fa-chart-bar"
    collapse-id="addGameFormCollapse"
    header-class="add-game-header"
    icon-class="add-game-icon"
    title-class="add-game-title"
    chevron-class="add-game-chevron"
    chevron-id="addGameChevron"
  >
    <div class="d-flex justify-content-end mb-3">
      <IconButton variant="outline-secondary" size="sm" class="text-white" icon="fa-search" @click="toggleSearch">
        Search Game
      </IconButton>
    </div>

    <div v-if="showSearch" class="mb-4">
      <div class="mb-3">
        <InputLabel text="SEARCH BY GAME NAME" />
        <InputGroup
          v-model="searchQuery"
          placeholder="Type game name to search..."
          button-label="Search"
          button-icon="fa-search"
          button-class="text-white"
        />
      </div>
      <hr class="border-secondary" />
    </div>

    <form id="addGameForm">
      <GameFormFields prefix="add" />

      <FormActions>
        <IconButton type="submit" variant="secondary" class="text-white fw-bold" icon="fa-save">
          Save Game
        </IconButton>
        <IconButton type="reset" variant="outline-secondary" class="text-white">Clear</IconButton>
      </FormActions>
    </form>
  </CollapsibleCard>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import CollapsibleCard from '@/components/molecules/CollapsibleCard.vue';
import GameFormFields from '@/components/molecules/GameFormFields.vue';
import FormActions from '@/components/molecules/FormActions.vue';
import InputGroup from '@/components/molecules/InputGroup.vue';
import IconButton from '@/components/atoms/IconButton.vue';
import InputLabel from '@/components/atoms/InputLabel.vue';

const showSearch = ref(false);
const searchQuery = ref('');

const toggleSearch = () => {
  showSearch.value = !showSearch.value;
};
</script>
