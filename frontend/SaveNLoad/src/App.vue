<template>
  <RouterView />
  <ConfirmModal />
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import { useWorkerStatusSocket } from '@/composables/useWorkerStatusSocket';
import { useAuthStore } from '@/stores/auth';
import ConfirmModal from '@/components/organisms/ConfirmModal.vue';

const router = useRouter();
const authStore = useAuthStore();

useWorkerStatusSocket({
  onWorkerUnavailable: async () => {
    if (authStore.isLoggingOut || !authStore.user) {
      return;
    }
    if (router.currentRoute.value.path !== '/worker-required') {
      await router.push('/worker-required');
    }
  }
});
</script>
