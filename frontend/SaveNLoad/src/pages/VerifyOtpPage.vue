<template>
  <AuthLayout title="Save N Load" subtitle="We've sent a verification code to your email.">
    <form @submit.prevent="onSubmit">
      <div class="mb-3">
        <InputLabel text="EMAIL" />
        <TextInput v-model="email" type="email" placeholder="Enter your email" :invalid="!!fieldErrors?.email" required />
      </div>
      <div class="mb-3">
        <InputLabel text="6-Digit Verification Code" />
        <TextInput
          v-model="otpCode"
          input-class="text-center otp-input-code"
          placeholder="000000"
          maxlength="6"
          :invalid="!!fieldErrors?.otp_code"
          required
        />
      </div>
      <div class="d-grid mt-2">
        <IconButton type="button" variant="secondary" class="text-white fw-bold py-2" :disabled="loading" @click="onResend">
          RESEND CODE
        </IconButton>
      </div>
      <p class="text-white fs-6 text-center mt-3">
        Remember your password?
        <RouterLink to="/login" class="text-secondary text-decoration-none fs-6">Login</RouterLink>
      </p>
      <p class="text-white fs-6 text-center mt-2">
        Wrong email?
        <RouterLink to="/forgot-password" class="text-secondary text-decoration-none fs-6">Start Over</RouterLink>
      </p>
    </form>
  </AuthLayout>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import AuthLayout from '@/layouts/AuthLayout.vue';
import { useAuthStore } from '@/stores/auth';
import IconButton from '@/components/atoms/IconButton.vue';
import InputLabel from '@/components/atoms/InputLabel.vue';
import TextInput from '@/components/atoms/TextInput.vue';

const store = useAuthStore();
const router = useRouter();

const email = ref(store.otpEmail || '');
const otpCode = ref('');

watch(
  () => store.otpEmail,
  (next) => {
    if (next) {
      email.value = next;
    }
  }
);

const loading = computed(() => store.loading);
const fieldErrors = computed(() => store.fieldErrors);

const onSubmit = async () => {
  try {
    await store.verifyOtp({ email: email.value, otp_code: otpCode.value });
    await router.push('/reset-password');
  } catch {
    // handled by store
  }
};

const onResend = async () => {
  try {
    await store.resendOtp({ email: email.value });
  } catch {
    // handled by store
  }
};
</script>
