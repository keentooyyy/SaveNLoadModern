<template>
  <AuthLayout title="Save N Load" subtitle="Reset your password to regain access.">
    <form @submit.prevent="onSubmit">
      <div class="mb-3">
        <InputLabel text="EMAIL" />
        <TextInput v-model="email" type="email" placeholder="Enter your email" :invalid="!!fieldErrors?.email" required />
      </div>
      <div class="d-grid">
        <IconButton
          type="submit"
          variant="secondary"
          class="text-white fw-bold mt-3 py-2"
          :disabled="isSubmitting"
          :loading="isSubmitting"
        >
          SEND OTP
        </IconButton>
      </div>
      <AuthFooterLink prefix="Remember your password? " link-text="Login" to="/login" />
    </form>
  </AuthLayout>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import AuthLayout from '@/layouts/AuthLayout.vue';
import { useAuthStore } from '@/stores/auth';
import IconButton from '@/components/atoms/IconButton.vue';
import InputLabel from '@/components/atoms/InputLabel.vue';
import TextInput from '@/components/atoms/TextInput.vue';
import AuthFooterLink from '@/components/molecules/AuthFooterLink.vue';

const store = useAuthStore();
const router = useRouter();
const email = ref('');

const loading = computed(() => store.loading);
const fieldErrors = computed(() => store.fieldErrors);
const submitting = ref(false);
const isSubmitting = computed(() => loading.value || submitting.value);

const onSubmit = async () => {
  if (isSubmitting.value) {
    return;
  }
  submitting.value = true;
  try {
    await store.forgotPassword({ email: email.value });
    await router.push('/verify-otp');
  } catch {
    // handled by store
  } finally {
    submitting.value = false;
  }
};
</script>
