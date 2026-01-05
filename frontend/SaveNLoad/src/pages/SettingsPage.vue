<template>
  <AppLayout>
    <div class="container-fluid px-0">
      <PageHeader title="Settings" />
      <div class="px-4 pt-4 pb-5">
        <SettingsPanel />
        <div class="mt-4" v-if="isAdmin">
          <QueuePanel />
        </div>
        <div class="mt-4" v-if="isAdmin">
          <AccountTable :users="users" />
        </div>
        <div class="mt-4">
          <ModalShell title="Manage game" subtitle="Preview of the admin modal">
            <p class="text-secondary mb-0">Wire this modal to game management endpoints.</p>
          </ModalShell>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import PageHeader from '@/components/organisms/PageHeader.vue';
import SettingsPanel from '@/components/organisms/SettingsPanel.vue';
import QueuePanel from '@/components/organisms/QueuePanel.vue';
import AccountTable from '@/components/organisms/AccountTable.vue';
import ModalShell from '@/components/organisms/ModalShell.vue';
import AppLayout from '@/layouts/AppLayout.vue';

const isAdmin = ref(true);
const users = [];
</script>
