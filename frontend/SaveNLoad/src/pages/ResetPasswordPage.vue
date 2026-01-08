<template>
  <AuthLayout
    title="Save N Load"
    subtitle="Set your new password."
    :on-reset="resetStatus"
  >
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
        <IconButton
          type="submit"
          variant="secondary"
          class="text-white fw-bold mt-3 py-2"
          :disabled="isSubmitting"
          :loading="isSubmitting"
        >
          RESET PASSWORD
        </IconButton>
      </div>
      <AuthFooterLink prefix="Remember your password? " link-text="Login" to="/login" />
    </form>
  </AuthLayout>
</template>

<script setup lang="ts">
import { reactive, computed, ref } from 'vue';
import AuthLayout from '@/layouts/AuthLayout.vue';
import PasswordField from '@/components/molecules/PasswordField.vue';
import { useAuthStore } from '@/stores/auth';
import IconButton from '@/components/atoms/IconButton.vue';
import InputLabel from '@/components/atoms/InputLabel.vue';
import AuthFooterLink from '@/components/molecules/AuthFooterLink.vue';
import { useAuthConfig } from '@/composables/useAuthConfig';

const store = useAuthStore();

const form = reactive({
  newPassword: '',
  confirmPassword: ''
});

const loading = computed(() => store.loading);
const fieldErrors = computed(() => store.fieldErrors);
const submitting = ref(false);
const isSubmitting = computed(() => loading.value || submitting.value);

useAuthConfig({ requireEmailFlow: true, loadAuthConfig: () => store.loadAuthConfig() });

const resetStatus = () => {
  store.resetStatus();
};

const onSubmit = async () => {
  if (isSubmitting.value) {
    return;
  }
  submitting.value = true;
  try {
    await store.resetPassword({
      new_password: form.newPassword,
      confirm_password: form.confirmPassword
    });
    window.location.assign('/');
  } catch {
    // handled by store
  } finally {
    submitting.value = false;
  }
};

</script>
