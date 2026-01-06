<template>
  <AuthLayout title="Save N Load" subtitle="Managing saves has never been easier.">
    <form @submit.prevent="onSubmit">
      <div class="mb-3">
        <InputLabel text="USERNAME OR EMAIL" />
        <TextInput
          v-model="form.username"
          placeholder="Enter your username or email"
          :invalid="!!fieldErrors?.username"
          required
        />
      </div>
      <div class="mb-2">
        <div class="d-flex justify-content-between align-items-center">
          <InputLabel text="PASSWORD" label-class="mb-0" />
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
        <IconButton type="submit" variant="secondary" class="text-white fw-bold mt-3 py-2" :disabled="loading" :loading="loading">
          LOGIN
        </IconButton>
      </div>
      <p class="text-white fs-6 text-center mt-3">
        Don't have an account?
        <RouterLink to="/register" class="text-secondary text-decoration-none fs-6">Create an account</RouterLink>
      </p>
    </form>
  </AuthLayout>
</template>

<script setup lang="ts">
import { reactive, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import AuthLayout from '@/layouts/AuthLayout.vue';
import PasswordField from '@/components/molecules/PasswordField.vue';
import { useAuthStore } from '@/stores/auth';
import { useDashboardStore } from '@/stores/dashboard';
import IconButton from '@/components/atoms/IconButton.vue';
import InputLabel from '@/components/atoms/InputLabel.vue';
import TextInput from '@/components/atoms/TextInput.vue';

const store = useAuthStore();
const dashboardStore = useDashboardStore();
const router = useRouter();

const form = reactive({
  username: '',
  password: '',
  rememberMe: false
});

const loading = computed(() => store.loading);
const fieldErrors = computed(() => store.fieldErrors);

const clearFieldError = (key: string) => {
  if (store.fieldErrors && store.fieldErrors[key]) {
    const next = { ...store.fieldErrors };
    delete next[key];
    store.fieldErrors = Object.keys(next).length ? next : null;
  }
  if (store.error) {
    store.error = '';
  }
};

watch(() => form.username, () => clearFieldError('username'));
watch(() => form.password, () => clearFieldError('password'));

const onSubmit = async () => {
  try {
    await store.login({
      username: form.username,
      password: form.password,
      rememberMe: form.rememberMe
    });
    try {
      await dashboardStore.loadDashboard();
      await router.push('/dashboard');
    } catch (err: any) {
      if (err?.status === 503) {
        await router.push('/worker-required');
        return;
      }
      if (err?.status === 401) {
        return;
      }
      await router.push('/dashboard');
    }
  } catch {
    // handled by store
  }
};
</script>
