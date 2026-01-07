<template>
  <AppLayout>
    <div class="container-fluid px-0">
      <PageHeader
        title="Settings"
        :user-label="headerName"
        :user-role="headerRole"
        @profile="goToProfile"
        @settings="goToSettings"
        @logout="onLogout"
      />
      <div>
        <AddGamePanel v-if="isAdmin" />
        <AdminSettingsPanel v-if="isAdmin" />
        <ManageAccountsPanel v-if="isAdmin" />
        <OperationQueuePanel v-if="isAdmin" />
        <GuestUpgradePanel v-if="isGuest" />
        <AccountSettingsPanel v-if="!isGuest" />
      </div>
    </div>
    <ManageGameModal v-if="isAdmin" />
  </AppLayout>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import PageHeader from '@/components/organisms/PageHeader.vue';
import AppLayout from '@/layouts/AppLayout.vue';
import AddGamePanel from '@/components/organisms/AddGamePanel.vue';
import AdminSettingsPanel from '@/components/organisms/AdminSettingsPanel.vue';
import ManageAccountsPanel from '@/components/organisms/ManageAccountsPanel.vue';
import OperationQueuePanel from '@/components/organisms/OperationQueuePanel.vue';
import AccountSettingsPanel from '@/components/organisms/AccountSettingsPanel.vue';
import ManageGameModal from '@/components/organisms/ManageGameModal.vue';
import GuestUpgradePanel from '@/components/organisms/GuestUpgradePanel.vue';
import { useAuthStore } from '@/stores/auth';
import { useRouter } from 'vue-router';

const authStore = useAuthStore();
const router = useRouter();

const headerName = computed(() => authStore.user?.username || '');
const headerRole = computed(() => (authStore.user?.role || '').toUpperCase());

const resolveAdmin = (user: { role?: string } | null) => {
  return user?.role === 'admin';
};

const isAdmin = computed(() => resolveAdmin(authStore.user));
const isGuest = computed(() => authStore.user?.is_guest);

const goToSettings = () => router.push('/settings');
const goToProfile = () => router.push('/settings');
const onLogout = async () => {
  try {
    await authStore.logout();
  } catch {
    // ignore
  } finally {
    await router.push('/login');
  }
};

</script>
