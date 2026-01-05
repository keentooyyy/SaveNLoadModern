<template>
  <RouterView />
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import { useWorkerStatusSocket } from '@/composables/useWorkerStatusSocket';

const router = useRouter();

useWorkerStatusSocket({
  onWorkerUnavailable: async () => {
    if (router.currentRoute.value.path !== '/worker-required') {
      await router.push('/worker-required');
    }
  }
});
</script>
