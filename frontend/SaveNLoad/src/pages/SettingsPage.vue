<template>
  <AppLayout>
    <div class="container-fluid px-0">
      <PageHeader title="Settings" />
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
import { ref } from 'vue';
import PageHeader from '@/components/organisms/PageHeader.vue';
import AppLayout from '@/layouts/AppLayout.vue';
import AddGamePanel from '@/components/organisms/AddGamePanel.vue';
import ManageAccountsPanel from '@/components/organisms/ManageAccountsPanel.vue';
import OperationQueuePanel from '@/components/organisms/OperationQueuePanel.vue';
import AccountSettingsPanel from '@/components/organisms/AccountSettingsPanel.vue';
import ManageGameModal from '@/components/organisms/ManageGameModal.vue';
import { useRouter } from 'vue-router';

const isAdmin = ref(true);
const router = useRouter();

</script>
