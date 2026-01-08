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
    <div v-if="isRawgEnabled" class="d-flex justify-content-end mb-3">
      <IconButton variant="outline-secondary" size="sm" class="text-white" icon="fa-search" @click="toggleSearch">
        Search Game
      </IconButton>
    </div>

    <div v-if="isRawgEnabled && showSearch" class="mb-4">
      <div class="mb-3">
        <InputLabel text="SEARCH BY GAME NAME" />
        <InputGroup
          v-model="searchQuery"
          placeholder="Type game name to search..."
          button-label="Search"
          button-icon="fa-search"
          button-class="text-white"
          @action="onSearch"
        />
      </div>
      <hr class="border-secondary" />
    </div>

    <form id="addGameForm" @submit.prevent="onSubmit" @reset.prevent="onReset">
      <GameFormFields
        prefix="add"
        v-model:banner-url="bannerUrl"
        v-model:game-name="gameName"
        v-model:save-locations="saveLocations"
      />

      <FormActions>
        <IconButton type="submit" variant="secondary" class="text-white fw-bold" icon="fa-save" :disabled="saving">
          Save Game
        </IconButton>
        <IconButton type="reset" variant="outline-secondary" class="text-white" :disabled="saving">Clear</IconButton>
      </FormActions>
    </form>

    <GameSearchModal
      v-if="isRawgEnabled"
      v-model:query="modalQuery"
      :open="searchModalOpen"
      :results="searchResults"
      :loading="searchLoading"
      :error="searchError"
      @search="onModalSearch"
      @select="onSelectGame"
      @close="searchModalOpen = false"
    />
    <Teleport v-if="isRawgEnabled" to="body">
      <div
        v-if="searchLoading"
        class="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center bg-dark bg-opacity-75 search-overlay"
      >
        <div class="text-center text-white">
          <div class="spinner-border" role="status" aria-live="polite">
            <span class="visually-hidden">Loading...</span>
          </div>
          <p class="mt-3 mb-0">Searching for games...</p>
        </div>
      </div>
    </Teleport>
  </CollapsibleCard>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import CollapsibleCard from '@/components/molecules/CollapsibleCard.vue';
import GameFormFields from '@/components/molecules/GameFormFields.vue';
import FormActions from '@/components/molecules/FormActions.vue';
import InputGroup from '@/components/molecules/InputGroup.vue';
import IconButton from '@/components/atoms/IconButton.vue';
import InputLabel from '@/components/atoms/InputLabel.vue';
import GameSearchModal from '@/components/organisms/GameSearchModal.vue';
import { notify } from '@/utils/notify';
const props = defineProps<{
  createGame: (payload: { name: string; save_file_locations: string[]; banner?: string }) => Promise<any>;
  rawgEnabled?: boolean | null;
}>();

const API_BASE = import.meta.env.VITE_API_BASE;

const isRawgEnabled = computed(() => props.rawgEnabled !== false);
const showSearch = ref(false);
const searchQuery = ref('');
const modalQuery = ref('');
const searchResults = ref<any[]>([]);
const searchLoading = ref(false);
const searchError = ref('');
const searchModalOpen = ref(false);

const bannerUrl = ref('');
const gameName = ref('');
const saveLocations = ref<string[]>(['']);
const saving = ref(false);

const toggleSearch = () => {
  if (!isRawgEnabled.value) {
    notify.warning('Game search is currently disabled by the admin.');
    return;
  }
  showSearch.value = !showSearch.value;
};

const showSearchModal = () => {
  searchModalOpen.value = true;
};

const performSearch = async (query: string) => {
  const trimmed = query.trim();
  if (trimmed.length < 2) {
    searchResults.value = [];
    searchError.value = 'Enter at least 2 characters.';
    showSearchModal();
    return;
  }

  searchLoading.value = true;
  searchError.value = '';
  try {
    const response = await fetch(`${API_BASE}/settings/search?q=${encodeURIComponent(trimmed)}`, {
      credentials: 'include'
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      searchError.value = data?.error || data?.message || '';
      searchResults.value = [];
    } else {
      searchResults.value = data?.games || [];
    }
  } catch {
    searchError.value = '';
    searchResults.value = [];
  } finally {
    searchLoading.value = false;
    showSearchModal();
  }
};

const onSearch = () => {
  modalQuery.value = searchQuery.value;
  void performSearch(searchQuery.value);
};

const onModalSearch = () => {
  void performSearch(modalQuery.value);
};

const onSelectGame = (game: any) => {
  gameName.value = game?.name || '';
  bannerUrl.value = game?.banner || '';
  const locations = Array.isArray(game?.save_file_locations) ? game.save_file_locations : [];
  saveLocations.value = locations.length ? [...locations] : [''];
  searchModalOpen.value = false;
};

const onReset = () => {
  bannerUrl.value = '';
  gameName.value = '';
  saveLocations.value = [''];
};

const onSubmit = async () => {
  const name = gameName.value.trim();
  const locations = saveLocations.value.map(location => location.trim()).filter(Boolean);
  saving.value = true;
  try {
    await props.createGame({
      name,
      save_file_locations: locations,
      banner: bannerUrl.value.trim() || ''
    });
    onReset();
  } finally {
    saving.value = false;
  }
};

if (!isRawgEnabled.value) {
  showSearch.value = false;
  searchModalOpen.value = false;
}
</script>

<style scoped>
.search-overlay {
  z-index: 2000; /* ensure it covers sidebar and modals */
}
</style>
