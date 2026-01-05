<template>
  <AuthLayout title="Save N Load" subtitle="Reset your password to regain access.">
    <form @submit.prevent="onSubmit">
      <div v-if="error" class="alert alert-warning mb-3">{{ error }}</div>
      <div class="mb-3">
        <label class="fs-6 opacity-50">EMAIL</label>
        <input
          class="color-primary form-control bg-primary border border-1 border-secondary rounded-1 py-2 text-white"
          type="email"
          v-model="email"
          placeholder="Enter your email"
          required
        />
      </div>
      <div class="d-grid">
        <button type="submit" class="btn btn-secondary text-white fw-bold mt-3 py-2" :disabled="loading">
          SEND OTP
        </button>
      </div>
      <p class="text-white fs-6 text-center mt-3">
        Remember your password?
        <RouterLink to="/login" class="text-secondary text-decoration-none fs-6">Login</RouterLink>
      </p>
    </form>
  </AuthLayout>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import AuthLayout from '@/layouts/AuthLayout.vue';
import { useAuthStore } from '@/stores/auth';

const store = useAuthStore();
const router = useRouter();
const email = ref('');

const loading = computed(() => store.loading);
const error = computed(() => store.error);

const onSubmit = async () => {
  try {
    await store.forgotPassword({ email: email.value });
    await router.push('/verify-otp');
  } catch {
    // handled by store
  }
};
</script>
