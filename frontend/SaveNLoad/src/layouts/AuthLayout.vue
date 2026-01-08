<template>
  <div class="min-vh-100 overflow-auto" style="overflow-x: hidden;">
    <div class="container mt-5">
      <div class="row justify-content-center">
        <div class="col-12 col-md-8 col-lg-6 col-xl-5">
          <AuthCard :title="title" :subtitle="subtitle">
            <slot />
          </AuthCard>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import AuthCard from '@/components/organisms/AuthCard.vue';

const props = defineProps({
  title: String,
  subtitle: String,
  onReset: { type: Function, default: null }
});

onMounted(() => {
  if (props.onReset) {
    props.onReset();
  }
});
</script>

<style scoped>
</style>
