<template>
  <AuthLayout title="Save N Load" subtitle="We've sent a verification code to your email.">
    <form @submit.prevent="onSubmit">
      <div class="mb-3">
        <label class="fs-6 opacity-50">EMAIL</label>
        <input
          class="color-primary form-control bg-primary border border-1 border-secondary rounded-1 py-2 text-white"
          :class="{ 'is-invalid': fieldErrors?.email }"
          type="email"
          v-model="email"
          placeholder="Enter your email"
          required
        />
      </div>
      <div class="mb-3">
        <label class="fs-6 opacity-50">6-Digit Verification Code</label>
        <input
          class="color-primary form-control bg-primary border border-1 border-secondary rounded-1 py-2 text-white text-center otp-input-code"
          :class="{ 'is-invalid': fieldErrors?.otp_code }"
          type="text"
          v-model="otpCode"
          placeholder="000000"
          maxlength="6"
          required
        />
      </div>
      <div class="d-grid mt-2">
        <button type="button" class="btn btn-secondary text-white fw-bold py-2" :disabled="loading" @click="onResend">
          RESEND CODE
        </button>
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
