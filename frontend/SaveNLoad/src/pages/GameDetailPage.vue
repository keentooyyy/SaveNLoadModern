<template>
  <AppLayout>
    <div class="container-fluid px-0">
      <PageHeader
        title="Game Details"
        :user-label="headerName"
        :user-role="headerRole"
        @profile="goToProfile"
        @settings="goToSettings"
        @logout="onLogout"
      />
      <div class="container-fluid px-3 px-md-4">
        <div v-if="loading" class="text-center py-5">
          <div class="spinner-border text-secondary" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
          <p class="text-white-50 mt-2 mb-0">Loading game data...</p>
        </div>
        <div v-else-if="error" class="alert alert-danger bg-danger bg-opacity-25 border-danger text-white">
          {{ error }}
        </div>
        <div v-else class="row g-4 justify-content-center mt-3">
          <div class="col-12 col-lg-8">
            <div class="card bg-primary border-secondary">
              <div class="card-body">
                <h5 class="text-white mb-3">Edit Game</h5>
                <form @submit.prevent="onSave">
                  <GameFormFields
                    prefix="detail"
                    v-model:banner-url="bannerUrl"
                    v-model:game-name="gameName"
                    v-model:save-locations="saveLocations"
                  />
                  <div class="d-flex gap-2 justify-content-end mt-3">
                    <IconButton type="button" variant="outline-secondary" class="text-white" @click="goBack">
                      Back
                    </IconButton>
                    <IconButton type="submit" variant="secondary" class="text-white" :loading="saving" :disabled="saving">
                      Save Changes
                    </IconButton>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import AppLayout from '@/layouts/AppLayout.vue';
import PageHeader from '@/components/organisms/PageHeader.vue';
import GameFormFields from '@/components/molecules/GameFormFields.vue';
import IconButton from '@/components/atoms/IconButton.vue';
import { useDashboardStore } from '@/stores/dashboard';
import { useSettingsStore } from '@/stores/settings';
import { useAuthStore } from '@/stores/auth';

const route = useRoute();
const router = useRouter();
const dashboardStore = useDashboardStore();
const settingsStore = useSettingsStore();
const authStore = useAuthStore();

const gameId = computed(() => Number(route.params.id));
const bannerUrl = ref('');
const gameName = ref('');
const saveLocations = ref<string[]>(['']);
const loading = ref(true);
const saving = ref(false);
const error = ref('');

const headerName = computed(() => dashboardStore.user?.username || authStore.user?.username || '');
const headerRole = computed(() => (dashboardStore.user?.role || authStore.user?.role || '').toUpperCase());

const loadGame = async () => {
  loading.value = true;
  error.value = '';
  try {
    await dashboardStore.loadDashboard();
    const game = dashboardStore.games.find((item) => item.id === gameId.value);
    if (!game) {
      await router.replace('/dashboard');
      return;
    }
    gameName.value = game.title || '';
    bannerUrl.value = game.image || '';
    const locations = Array.isArray(game.save_file_locations) ? game.save_file_locations : [];
    saveLocations.value = locations.length ? [...locations] : [''];
  } catch (err: any) {
    error.value = err?.message || 'Failed to load game.';
  } finally {
    loading.value = false;
  }
};

const onSave = async () => {
  if (saving.value || !gameId.value) {
    return;
  }
  saving.value = true;
  try {
    await settingsStore.updateGame(gameId.value, {
      name: gameName.value.trim(),
      banner: bannerUrl.value.trim(),
      save_file_locations: saveLocations.value.map((loc) => loc.trim()).filter(Boolean)
    });
    await dashboardStore.loadDashboard();
  } catch {
    // errors are surfaced via store notifications
  } finally {
    saving.value = false;
  }
};

const goBack = () => {
  router.back();
};

onMounted(() => {
  void loadGame();
});

const goToSettings = () => window.location.assign('/settings');
const goToProfile = () => window.location.assign('/settings');
const onLogout = async () => {
  try {
    await authStore.logout();
  } catch {
    // ignore
  } finally {
    window.location.assign('/login');
  }
};
</script>
