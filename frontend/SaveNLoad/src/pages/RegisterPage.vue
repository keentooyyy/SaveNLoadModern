<template>
  <AuthLayout title="Save N Load" subtitle="Create your account to get started.">
    <form @submit.prevent="onSubmit">
      <div v-if="error" class="alert alert-warning mb-3">{{ error }}</div>
      <div class="mb-3">
        <label class="fs-6 opacity-50">USERNAME</label>
        <input
          class="color-primary form-control bg-primary border border-1 border-secondary rounded-1 py-2 text-white"
          type="text"
          v-model="form.username"
          placeholder="Enter your username"
          required
        />
      </div>
      <div class="mb-3">
        <label class="fs-6 opacity-50">EMAIL</label>
        <input
          class="color-primary form-control bg-primary border border-1 border-secondary rounded-1 py-2 text-white"
          type="email"
          v-model="form.email"
          placeholder="Enter your email"
          required
        />
      </div>
      <div class="mb-3">
        <label class="fs-6 mb-0 opacity-50">PASSWORD</label>
        <PasswordField v-model="form.password" placeholder="Enter your password" />
      </div>
      <div class="mb-3">
        <label class="fs-6 mb-0 opacity-50">REPEAT PASSWORD</label>
        <PasswordField v-model="form.repeatPassword" placeholder="Repeat your password" />
      </div>
      <div class="d-grid">
        <button type="submit" class="btn btn-secondary text-white fw-bold mt-3 py-2" :disabled="loading">
          REGISTER
        </button>
      </div>
      <p class="text-white fs-6 text-center mt-3">
        Already have an account?
        <RouterLink to="/login" class="text-secondary text-decoration-none fs-6">Login</RouterLink>
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
  email: '',
  password: '',
  repeatPassword: ''
});

const loading = computed(() => store.loading);
const error = computed(() => store.error);

const onSubmit = async () => {
  try {
    await store.register({
      username: form.username,
      email: form.email,
      password: form.password,
      repeatPassword: form.repeatPassword
    });
    await router.push('/login');
  } catch {
    // handled by store
  }
};
</script>
