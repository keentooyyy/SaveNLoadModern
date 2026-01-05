<template>
  <AuthLayout title="Save N Load" subtitle="Managing saves has never been easier.">
    <form @submit.prevent="onSubmit">
      <div class="mb-3">
        <label class="fs-6 opacity-50">USERNAME OR EMAIL</label>
        <input
          class="color-primary form-control bg-primary border border-1 border-secondary rounded-1 py-2 text-white"
          :class="{ 'is-invalid': fieldErrors?.username }"
          type="text"
          v-model="form.username"
          placeholder="Enter your username or email"
          required
        />
      </div>
      <div class="mb-2">
        <div class="d-flex justify-content-between align-items-center">
          <label class="fs-6 mb-0 opacity-50">PASSWORD</label>
          <RouterLink to="/forgot-password" class="text-secondary text-decoration-none fs-6" tabindex="-1">
            Forgot Password?
          </RouterLink>
        </div>
        <PasswordField v-model="form.password" placeholder="Enter your password" :invalid="!!fieldErrors?.password" />
      </div>
      <div class="mb-3">
        <div class="form-check">
          <input
            class="form-check-input bg-primary border-secondary"
            type="checkbox"
            id="rememberMe"
            v-model="form.rememberMe"
          />
          <label class="form-check-label text-white fs-6" for="rememberMe">Remember Me</label>
        </div>
      </div>
      <div class="d-grid">
        <button type="submit" class="btn btn-secondary text-white fw-bold mt-3 py-2" :disabled="loading">
          LOGIN
        </button>
      </div>
      <p class="text-white fs-6 text-center mt-3">
        Don't have an account?
        <RouterLink to="/register" class="text-secondary text-decoration-none fs-6">Create an account</RouterLink>
      </p>
    </form>
  </AuthLayout>
</template>

<script setup lang="ts">
import { reactive, computed } from 'vue';
import { useRouter } from 'vue-router';
import AuthLayout from '@/layouts/AuthLayout.vue';
import PasswordField from '@/components/molecules/PasswordField.vue';
import { useAuthStore } from '@/stores/auth';

const store = useAuthStore();
const router = useRouter();

const form = reactive({
  username: '',
  password: '',
  rememberMe: false
});

const loading = computed(() => store.loading);
const fieldErrors = computed(() => store.fieldErrors);

const onSubmit = async () => {
  try {
    await store.login({
      username: form.username,
      password: form.password,
      rememberMe: form.rememberMe
    });
    await router.push('/dashboard');
  } catch {
    // handled by store
  }
};
</script>
