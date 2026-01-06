<template>
  <AuthLayout title="Save N Load" subtitle="Create your account to get started.">
    <form @submit.prevent="onSubmit">
      <div class="mb-3">
        <InputLabel text="USERNAME" />
        <TextInput
          v-model="form.username"
          placeholder="Enter your username"
          :invalid="!!fieldErrors?.username"
          required
        />
      </div>
      <div class="mb-3">
        <InputLabel text="EMAIL" />
        <TextInput v-model="form.email" type="email" placeholder="Enter your email" :invalid="!!fieldErrors?.email" required />
      </div>
      <div class="mb-3">
        <InputLabel text="PASSWORD" label-class="mb-0" />
        <PasswordField v-model="form.password" placeholder="Enter your password" :invalid="!!fieldErrors?.password" />
      </div>
      <div class="mb-3">
        <InputLabel text="REPEAT PASSWORD" label-class="mb-0" />
        <PasswordField
          v-model="form.repeatPassword"
          placeholder="Repeat your password"
          :invalid="!!fieldErrors?.repeatPassword"
        />
      </div>
      <div class="d-grid">
        <IconButton type="submit" variant="secondary" class="text-white fw-bold mt-3 py-2" :disabled="loading" :loading="loading">
          REGISTER
        </IconButton>
      </div>
      <p class="text-white fs-6 text-center mt-3">
        Already have an account?
        <RouterLink to="/login" class="text-secondary text-decoration-none fs-6">Login</RouterLink>
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
import IconButton from '@/components/atoms/IconButton.vue';
import InputLabel from '@/components/atoms/InputLabel.vue';
import TextInput from '@/components/atoms/TextInput.vue';

const store = useAuthStore();
const router = useRouter();

const form = reactive({
  username: '',
  email: '',
  password: '',
  repeatPassword: ''
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
watch(() => form.email, () => clearFieldError('email'));
watch(() => form.password, () => clearFieldError('password'));
watch(() => form.repeatPassword, () => clearFieldError('repeatPassword'));

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
