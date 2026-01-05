<template>
  <div class="login-page">
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
import AuthCard from '@/components/organisms/AuthCard.vue';

defineProps({
  title: String,
  subtitle: String
});
</script>
