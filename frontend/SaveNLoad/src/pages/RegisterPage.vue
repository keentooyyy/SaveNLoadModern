<template>
  <AuthLayout
    title="Save N Load"
    subtitle="Create your account to get started."
    :on-reset="resetStatus"
  >
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
      <div v-if="showEmailField" class="mb-3">
        <InputLabel text="EMAIL" />
        <TextInput
          v-model="form.email"
          type="email"
          placeholder="Enter your email"
          :invalid="!!fieldErrors?.email"
          required
        />
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
        <IconButton
          type="submit"
          variant="secondary"
          class="text-white fw-bold mt-3 py-2"
          :disabled="isSubmitting"
          :loading="isSubmitting"
        >
          REGISTER
        </IconButton>
      </div>
      <AuthFooterLink prefix="Already have an account? " link-text="Login" to="/" />
    </form>
  </AuthLayout>
</template>

<script setup lang="ts">
import { reactive, computed, watch, ref } from 'vue';
import AuthLayout from '@/layouts/AuthLayout.vue';
import PasswordField from '@/components/molecules/PasswordField.vue';
import { useAuthStore } from '@/stores/auth';
import IconButton from '@/components/atoms/IconButton.vue';
import InputLabel from '@/components/atoms/InputLabel.vue';
import TextInput from '@/components/atoms/TextInput.vue';
import AuthFooterLink from '@/components/molecules/AuthFooterLink.vue';
import { useAuthConfig } from '@/composables/useAuthConfig';

const store = useAuthStore();

const form = reactive({
  username: '',
  email: '',
  password: '',
  repeatPassword: ''
});

const loading = computed(() => store.loading);
const fieldErrors = computed(() => store.fieldErrors);
const submitting = ref(false);
const isSubmitting = computed(() => loading.value || submitting.value);
const showEmailField = computed(() => (
  store.authConfigLoaded && store.authConfig.emailRegistrationRequired
));

useAuthConfig({ loadAuthConfig: () => store.loadAuthConfig() });

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

const resetStatus = () => {
  store.resetStatus();
};

watch(() => form.username, () => clearFieldError('username'));
watch(() => form.email, () => clearFieldError('email'));
watch(() => form.password, () => clearFieldError('password'));
watch(() => form.repeatPassword, () => clearFieldError('repeatPassword'));

const onSubmit = async () => {
  if (isSubmitting.value) {
    return;
  }
  submitting.value = true;
  try {
    const payload = {
      username: form.username,
      password: form.password,
      repeatPassword: form.repeatPassword
    } as { username: string; email?: string; password: string; repeatPassword: string };
    if (showEmailField.value) {
      payload.email = form.email;
    }
    await store.register(payload);
    window.location.assign('/login');
  } catch {
    // handled by store
  } finally {
    submitting.value = false;
  }
};

</script>
