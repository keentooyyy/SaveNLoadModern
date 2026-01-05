<template>
  <AuthLayout title="Save N Load" subtitle="We've sent a verification code to your email.">
    <form @submit.prevent>
      <div class="mb-3">
        <label class="fs-6 opacity-50">6-Digit Verification Code</label>
        <input
          class="color-primary form-control bg-primary border border-1 border-secondary rounded-1 py-2 text-white text-center otp-input-code"
          type="text"
          placeholder="000000"
          maxlength="6"
          required
        />
      </div>
      <div class="d-grid mt-2">
        <button type="button" class="btn btn-secondary text-white fw-bold py-2">RESEND CODE</button>
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
import AuthLayout from '@/layouts/AuthLayout.vue';
</script>
