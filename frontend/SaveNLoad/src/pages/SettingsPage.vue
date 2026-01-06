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
        <ManageAccountsPanel v-if="isAdmin" />
        <OperationQueuePanel v-if="isAdmin" />
        <AccountSettingsPanel />
      </div>
    </div>
    <ManageGameModal v-if="isAdmin" />
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import PageHeader from '@/components/organisms/PageHeader.vue';
import AppLayout from '@/layouts/AppLayout.vue';
import AddGamePanel from '@/components/organisms/AddGamePanel.vue';
import ManageAccountsPanel from '@/components/organisms/ManageAccountsPanel.vue';
import OperationQueuePanel from '@/components/organisms/OperationQueuePanel.vue';
import AccountSettingsPanel from '@/components/organisms/AccountSettingsPanel.vue';
import ManageGameModal from '@/components/organisms/ManageGameModal.vue';
import { useAuthStore } from '@/stores/auth';
import { useSettingsStore } from '@/stores/settings';
import { computed } from 'vue';
import { useRouter } from 'vue-router';

const isAdmin = ref(false);
const authStore = useAuthStore();
const settingsStore = useSettingsStore();
const router = useRouter();

const headerName = computed(() => settingsStore.currentUser?.username || authStore.user?.username || '');
const headerRole = computed(() => (settingsStore.currentUser?.role || authStore.user?.role || '').toUpperCase());

const resolveAdmin = (user: { role?: string } | null) => {
  return user?.role === 'admin';
};

onMounted(async () => {
  if (settingsStore.bootstrapLoaded) {
    const user = settingsStore.currentUser || authStore.user;
    isAdmin.value = resolveAdmin(user);
    return;
  }

  try {
    const data = await settingsStore.bootstrapSettings();
    const user = data?.user || settingsStore.currentUser;
    authStore.user = user as any;
    isAdmin.value = resolveAdmin(user);
  } catch {
    isAdmin.value = false;
  }
});

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
