<template>
  <AppLayout :version-label="versionLabel" :on-logout="onLogout" :on-load-version="loadVersion">
    <div class="container-fluid px-0">
      <PageHeader
        title="Settings"
        :user-label="headerName"
        :user-role="headerRole"
        @profile="goToProfile"
        @settings="goToSettings"
        @logout="onLogout"
      />
      <div v-if="isLoading" class="text-center py-5">
        <div class="spinner-border text-secondary" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
        <p class="text-white-50 mt-2 mb-0">Loading settings...</p>
      </div>
      <div v-else>
        <AddGamePanel v-if="isAdmin" :create-game="createGame" />
        <AdminSettingsPanel
          v-if="isAdmin"
          :load-settings="loadAdminSettings"
          :update-settings="updateAdminSettings"
          :check-health="checkAdminSettingsHealth"
          :reveal-settings="revealAdminSettings"
        />
        <ManageAccountsPanel
          v-if="isAdmin"
          :list-users="listUsers"
          :reset-user-password="resetUserPassword"
          :delete-user="deleteUser"
          :check-operation-status="checkOperationStatus"
        />
        <OperationQueuePanel
          v-if="isAdmin"
          :load-queue-stats="loadQueueStats"
          :clear-queue="clearQueue"
        />
        <WorkerManagementPanel
          v-if="isAdmin"
          :list-workers="listWorkers"
          :unclaim-all-workers="unclaimAllWorkers"
        />
        <GuestUpgradePanel
          v-if="isGuest"
          :migration-status="migrationStatus"
          :is-submitting="isSubmitting"
          :guest-credentials="guestCredentials"
          :current-username="currentUsername"
          :upgrade-guest="upgradeGuest"
          :refresh-user="refreshUser"
          :check-operation-status="checkOperationStatus"
          :clear-guest-credentials="clearGuestCredentials"
          :get-is-guest="getIsGuest"
        />
        <AccountSettingsPanel v-if="!isGuest" :email="accountEmail" :on-save="updateAccount" />
      </div>
    </div>
    <ManageGameModal v-if="isAdmin" />
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, toRef } from 'vue';
import PageHeader from '@/components/organisms/PageHeader.vue';
import AppLayout from '@/layouts/AppLayout.vue';
import AddGamePanel from '@/components/organisms/AddGamePanel.vue';
import AdminSettingsPanel from '@/components/organisms/AdminSettingsPanel.vue';
import ManageAccountsPanel from '@/components/organisms/ManageAccountsPanel.vue';
import OperationQueuePanel from '@/components/organisms/OperationQueuePanel.vue';
import AccountSettingsPanel from '@/components/organisms/AccountSettingsPanel.vue';
import ManageGameModal from '@/components/organisms/ManageGameModal.vue';
import GuestUpgradePanel from '@/components/organisms/GuestUpgradePanel.vue';
import WorkerManagementPanel from '@/components/organisms/WorkerManagementPanel.vue';
import { useAuthStore } from '@/stores/auth';
import { useMetaStore } from '@/stores/meta';
import { useSettingsStore } from '@/stores/settings';
import { useWorkerStatusSocket } from '@/composables/useWorkerStatusSocket';
import { getSharedWsToken } from '@/utils/wsToken';

const authStore = useAuthStore();
const metaStore = useMetaStore();
const settingsStore = useSettingsStore();
const suppressRedirectRef = toRef(authStore, 'suppressWorkerRedirect');
const isLoading = ref(true);

const headerName = computed(() => authStore.user?.username || '');
const headerRole = computed(() => (authStore.user?.role || '').toUpperCase());
const versionLabel = computed(() => metaStore.versionLabel);
const accountEmail = computed(() => authStore.user?.email || '');
const migrationStatus = computed(() => authStore.user?.guest_migration_status || '');
const isSubmitting = computed(() => authStore.loading);
const guestCredentials = computed(() => authStore.guestCredentials);
const currentUsername = computed(() => authStore.user?.username || '');

const resolveAdmin = (user: { role?: string } | null) => {
  return user?.role === 'admin';
};

const isAdmin = computed(() => resolveAdmin(authStore.user));
const isGuest = computed(() => authStore.user?.is_guest);

const goToSettings = () => window.location.assign('/settings');
const goToProfile = () => window.location.assign('/settings');
const onLogout = async () => {
  authStore.suppressWorkerRedirect = true;
  try {
    await authStore.logout();
  } catch {
    // ignore
  } finally {
    window.location.assign('/');
  }
};

const loadVersion = async () => {
  await metaStore.loadVersion();
};

useWorkerStatusSocket({
  userRef: computed(() => authStore.user),
  suppressRedirectRef,
  getWsToken: () => getSharedWsToken(),
  onWorkerUnavailable: () => {
    window.location.assign('/worker-required');
  }
});

const createGame = async (payload: { name: string; save_file_locations: string[]; banner?: string }) => (
  settingsStore.createGame(payload)
);

const updateAccount = async (payload: {
  email?: string;
  current_password?: string;
  new_password?: string;
  confirm_password?: string;
}) => {
  await settingsStore.updateAccount(payload);
};

const loadAdminSettings = async () => settingsStore.loadAdminSettings();
const updateAdminSettings = async (payload: Record<string, any>) => settingsStore.updateAdminSettings(payload);
const checkAdminSettingsHealth = async () => settingsStore.checkAdminSettingsHealth();
const revealAdminSettings = async (keys: string[], password: string) => (
  settingsStore.revealAdminSettings(keys, password)
);

const listUsers = async (query: string, page: number) => settingsStore.listUsers(query, page);
const resetUserPassword = async (userId: number) => settingsStore.resetUserPassword(userId);
const deleteUser = async (userId: number) => settingsStore.deleteUser(userId);
const checkOperationStatus = async (operationId: string) => settingsStore.checkOperationStatus(operationId);
const loadQueueStats = async () => settingsStore.queueStats();
const clearQueue = async () => settingsStore.cleanupQueue('all');
const listWorkers = async () => settingsStore.listWorkers();
const unclaimAllWorkers = async () => settingsStore.unclaimAllWorkers();
const upgradeGuest = async (payload: { username: string; email: string; password: string }) => (
  authStore.upgradeGuest(payload)
);
const refreshUser = async () => authStore.refreshUser();
const getIsGuest = () => !!authStore.user?.is_guest;
const clearGuestCredentials = () => {
  authStore.guestCredentials = null;
  try {
    window.sessionStorage.removeItem('savenload_guest_credentials');
  } catch {
    // ignore
  }
  try {
    window.localStorage.removeItem('savenload_guest_credentials');
  } catch {
    // ignore
  }
};

onMounted(async () => {
  try {
    await authStore.refreshUser();
    if (!authStore.user) {
      window.location.assign('/login');
      return;
    }
  } catch {
    window.location.assign('/login');
    return;
  } finally {
    isLoading.value = false;
  }
});

</script>
