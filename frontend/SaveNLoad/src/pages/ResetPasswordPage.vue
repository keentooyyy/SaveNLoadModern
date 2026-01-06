<template>
  <AuthLayout title="Save N Load" subtitle="Set your new password.">
    <form @submit.prevent="onSubmit">
      <div class="mb-3">
        <InputLabel text="NEW PASSWORD" />
        <PasswordField
          v-model="form.newPassword"
          placeholder="Enter new password"
          :invalid="!!fieldErrors?.new_password"
        />
      </div>
      <div class="mb-3">
        <InputLabel text="CONFIRM PASSWORD" />
        <PasswordField
          v-model="form.confirmPassword"
          placeholder="Confirm new password"
          :invalid="!!fieldErrors?.confirm_password"
        />
      </div>
      <div class="d-grid">
        <IconButton type="submit" variant="secondary" class="text-white fw-bold mt-3 py-2" :disabled="loading" :loading="loading">
          RESET PASSWORD
        </IconButton>
      </div>
      <p class="text-white fs-6 text-center mt-3">
        Remember your password?
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
import IconButton from '@/components/atoms/IconButton.vue';
import InputLabel from '@/components/atoms/InputLabel.vue';

const store = useAuthStore();
const router = useRouter();

const form = reactive({
  newPassword: '',
  confirmPassword: ''
});

const loading = computed(() => store.loading);
const fieldErrors = computed(() => store.fieldErrors);

const onSubmit = async () => {
  try {
    await store.resetPassword({
      new_password: form.newPassword,
      confirm_password: form.confirmPassword
    });
    await router.push('/login');
  } catch {
    // handled by store
  }
};
</script>
